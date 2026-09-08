"""Offline Linux enforcement spike. NOT installed or used by worker dispatch.

Broker must be the only writer in a private, harness-owned staging tree. All
untrusted processes see that tree through a read-only mount. External same-UID
host attackers, hostile mounts and concurrent harness writes are out of scope.
"""
import hashlib
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile


class Denied(ValueError):
    pass


PROTECTED = frozenset({
    'agents.md', 'agents.override.md', 'claude.md', 'claude.local.md',
    '.agents', '.codex', '.claude', '.git', '.github', '.agent-data',
    '.env', 'config.env', '.gitconfig', '.git-credentials', '.ssh',
    '.npmrc', '.pypirc', '.netrc',
})
WRITE_PHASES = frozenset({'IMPLEMENT', 'REVIEW', 'POST_IMPL_RETRY', 'TEST_FIX'})
READ_PHASES = frozenset({'TRIAGE', 'REPLY', 'VALIDATE', 'ADVERSARIAL_PLAN',
                         'POST_IMPL_REVIEW', 'CLEANUP'})
MAX_CONTENT = 1024 * 1024
DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC


def parts(path):
    if not isinstance(path, str) or len(path) > 4096:
        raise Denied('invalid path')
    result = path.split('/')
    if any(not re.fullmatch(r'[A-Za-z0-9_. -]+', p) or p in {'.', '..'}
           or p.casefold() in PROTECTED or p.casefold().startswith('.env.')
           for p in result):
        raise Denied('protected or noncanonical path')
    return result


def digest(content):
    return hashlib.sha256(content).hexdigest()


class Broker:
    """Serial, single-file operations; never shell out or accept launch options."""
    def __init__(self, root, phase):
        if phase not in WRITE_PHASES | READ_PHASES:
            raise Denied('unknown phase')
        self.phase = phase
        self.root_fd = os.open(root, DIR_FLAGS)

    def close(self):
        os.close(self.root_fd)

    def request(self, request):
        if not isinstance(request, dict):
            raise Denied('object required')
        op = request.get('op')
        keys = {'read': {'op', 'path'}, 'mkdir': {'op', 'path'},
                'put': {'op', 'path', 'content', 'expected'},
                'delete': {'op', 'path', 'expected'}}
        if not isinstance(op, str) or op not in keys or set(request) != keys[op]:
            raise Denied('unsupported operation or fields')
        if op != 'read' and self.phase not in WRITE_PHASES:
            raise Denied('read-only phase')
        components = parts(request['path'])
        parent = os.dup(self.root_fd)
        try:
            for component in components[:-1]:
                child = os.open(component, DIR_FLAGS, dir_fd=parent)
                os.close(parent)
                parent = child
            name = components[-1]
            if op == 'mkdir':
                os.mkdir(name, mode=0o755, dir_fd=parent)
                return {'created': True}
            old = None
            mode = 0o644
            try:
                fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
                             | os.O_CLOEXEC, dir_fd=parent)
            except FileNotFoundError:
                if op != 'put':
                    raise Denied('missing file') from None
            else:
                try:
                    info = os.fstat(fd)
                    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                        raise Denied('regular, singly linked files required')
                    if info.st_size > MAX_CONTENT:
                        raise Denied('file too large')
                    old = b''
                    while len(old) <= MAX_CONTENT:
                        chunk = os.read(fd, min(65536, MAX_CONTENT + 1 - len(old)))
                        if not chunk:
                            break
                        old += chunk
                    if len(old) > MAX_CONTENT:
                        raise Denied('file too large')
                    mode = 0o755 if info.st_mode & 0o111 else 0o644
                finally:
                    os.close(fd)
            if op == 'read':
                return {'content': old.decode('utf-8'), 'sha256': digest(old)}
            expected = digest(old) if old is not None else None
            if request['expected'] != expected:
                raise Denied('stale content')
            if op == 'delete':
                os.unlink(name, dir_fd=parent)
                return {'deleted': True}
            content = request['content']
            if not isinstance(content, str):
                raise Denied('UTF-8 text required')
            encoded = content.encode('utf-8')
            if len(encoded) > MAX_CONTENT:
                raise Denied('content too large')
            # Do not truncate an existing inode: publish a fresh file atomically.
            temporary = '.broker-' + os.urandom(16).hex()
            fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL
                         | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600, dir_fd=parent)
            try:
                with os.fdopen(fd, 'wb') as stream:
                    stream.write(encoded)
                    os.fchmod(stream.fileno(), mode)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, name, src_dir_fd=parent, dst_dir_fd=parent)
                os.fsync(parent)
            finally:
                try:
                    os.unlink(temporary, dir_fd=parent)
                except FileNotFoundError:
                    pass
            return {'sha256': digest(encoded)}
        except (OSError, UnicodeError) as error:
            raise Denied(type(error).__name__) from None
        finally:
            os.close(parent)


def sandbox_argv(source, fixture, argv):
    """Harness inputs only. Never accept these paths or argv from the worker.

    /usr and libraries are this host's runtime baseline, not a portable image.
    No host /etc, /home, /run, /tmp, sockets, auth files or source .git mounts.
    A production exporter must prepare the source tree without credentials.
    """
    command = ['/usr/bin/bwrap', '--unshare-all', '--unshare-user',
               '--disable-userns', '--die-with-parent',
               '--new-session', '--cap-drop', 'ALL', '--clearenv',
               '--ro-bind', '/usr', '/usr', '--symlink', 'usr/bin', '/bin',
               '--symlink', 'usr/lib', '/lib', '--symlink', 'usr/lib64', '/lib64',
               '--proc', '/proc', '--dev', '/dev', '--tmpfs', '/tmp',
               '--dir', '/home/worker', '--setenv', 'HOME', '/home/worker',
               '--setenv', 'PATH', '/usr/bin:/bin', '--setenv', 'LANG', 'C.UTF-8',
               '--ro-bind', str(Path(source).resolve()), '/workspace',
               '--ro-bind', str(Path(fixture).resolve()), '/fixture',
               '--chdir', '/workspace', '--remount-ro', '/']
    return command + ['--'] + list(argv)


def run_sandbox(source, fixture, argv, timeout=10):
    # File captures avoid descendants holding a pipe open after the init dies.
    # bwrap's PID-namespace init lifetime contains even setsid() descendants.
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        with subprocess.Popen(sandbox_argv(source, fixture, argv),
                              env={'PATH': '/usr/bin:/bin'}, stdin=subprocess.DEVNULL,
                              stdout=out, stderr=err, close_fds=True) as process:
            timed_out = False
            try:
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                process.terminate()
                try:
                    process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=1)
            out.seek(0)
            err.seek(0)
            return {'exit_code': process.returncode, 'timed_out': timed_out,
                    'stdout': out.read(2 * MAX_CONTENT).decode('utf-8', 'replace'),
                    'stderr': err.read(4096).decode('utf-8', 'replace')}


class Commands:
    """Prototype named command capability. No Claude rule-string translation.

    The fixture path and command are supplied by the harness at construction.
    Build scripts are arbitrary untrusted code, confined by run_sandbox; they
    never get the broker's write channel. This is NOT a global execve allowlist.
    """
    def __init__(self, source, fixture):
        self.source, self.fixture = source, fixture

    def request(self, request):
        if request != {'op': 'test'}:
            raise Denied('only the harness-configured test capability is supported')
        return run_sandbox(self.source, self.fixture,
                           ['/usr/bin/python3', '-I', '/fixture/check.py'])

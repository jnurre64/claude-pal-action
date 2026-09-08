"""Private source export and candidate validation; not a production importer.

Caller must hold exclusive ownership while snapshotting. No git commands, ignored
file discovery or credential detection are inferred here: supply a clean source
input. Known configuration/credential paths are omitted at every depth. Symlinks,
hardlinks, special files and oversized trees fail closed. Artifacts remain outside
installed runtime until import/recovery and source-revision gates are implemented.
"""
import hashlib
import os
from pathlib import Path
import re
import stat

from prototype import Denied, DIR_FLAGS, MAX_CONTENT, PROTECTED

INSTRUCTIONS = frozenset({'agents.md', 'agents.override.md', 'claude.md', 'claude.local.md'})
MAX_FILES = 10000
MAX_TOTAL = 32 * 1024 * 1024


def excluded(name):
    lower = name.casefold()
    return (lower in PROTECTED and lower not in INSTRUCTIONS) or lower.startswith('.env.')


def collect(root, *, reject_excluded=False):
    files, directories, total = {}, [], 0
    root_fd = os.open(root, DIR_FLAGS)

    def walk(fd, prefix=''):
        nonlocal total
        for name in sorted(os.listdir(fd)):
            if not re.fullmatch(r'[A-Za-z0-9_. -]+', name) or name in {'.', '..'}:
                raise Denied('unsupported filename')
            if excluded(name):
                if reject_excluded:
                    raise Denied('candidate contains configuration or credential path')
                continue
            relative = prefix + name
            info = os.stat(name, dir_fd=fd, follow_symlinks=False)
            if stat.S_ISDIR(info.st_mode):
                if name.casefold() in INSTRUCTIONS:
                    raise Denied('instruction paths must be files')
                if len(directories) >= MAX_FILES:
                    raise Denied('too many directories')
                directories.append(relative)
                child = os.open(name, DIR_FLAGS, dir_fd=fd)
                try:
                    walk(child, relative + '/')
                finally:
                    os.close(child)
            else:
                file_fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
                                  | os.O_CLOEXEC, dir_fd=fd)
                try:
                    info = os.fstat(file_fd)
                    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                        raise Denied('regular singly linked source files required')
                    content = b''
                    while len(content) <= MAX_CONTENT:
                        chunk = os.read(file_fd, min(65536, MAX_CONTENT + 1 - len(content)))
                        if not chunk:
                            break
                        content += chunk
                    total += len(content)
                    if len(content) > MAX_CONTENT or total > MAX_TOTAL or len(files) >= MAX_FILES:
                        raise Denied('source size limit exceeded')
                    files[relative] = {'content': content, 'sha256': hashlib.sha256(content).hexdigest(),
                                       'mode': 0o755 if info.st_mode & 0o111 else 0o644}
                finally:
                    os.close(file_fd)
    try:
        walk(root_fd)
        return files, directories
    except (OSError, RecursionError):
        raise Denied('unsafe or excessively deep source tree') from None
    finally:
        os.close(root_fd)


def export(source, destination):
    # Validate the whole input before publishing any snapshot. Destination must
    # be a new path under a harness-owned private directory, never worker-chosen.
    files, directories = collect(source)
    destination = Path(destination)
    destination.mkdir(mode=0o700)
    for relative in sorted(directories, key=lambda p: (p.count('/'), p)):
        (destination / relative).mkdir()
    for relative, data in files.items():
        path = destination / relative
        with path.open('xb') as stream:
            stream.write(data['content'])
        path.chmod(data['mode'])
    return {path: {'sha256': data['sha256'], 'mode': data['mode']} for path, data in files.items()}


def validate_candidate(candidate, baseline):
    """Return a checked diff for harness review; never modify the real worktree."""
    current, _ = collect(candidate, reject_excluded=True)
    changes = []
    for path in sorted(set(baseline) | set(current)):
        before = baseline.get(path)
        after = ({'sha256': current[path]['sha256'], 'mode': current[path]['mode']}
                 if path in current else None)
        if before == after:
            continue
        if any(part.casefold() in INSTRUCTIONS for part in path.split('/')):
            raise Denied('instruction change in candidate')
        changes.append({'path': path, 'before': before, 'after': after})
    return changes

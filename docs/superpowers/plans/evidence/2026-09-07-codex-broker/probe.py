"""Run outside the interactive sandbox. Disposable synthetic data only."""
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time
import uuid

from prototype import Broker, Commands, digest, run_sandbox


CHECK = r'''
import json, os, pathlib, socket, subprocess
root = pathlib.Path('/workspace')
config = json.loads(pathlib.Path('/fixture/probe.json').read_text())
results = {}
def denied(name, action):
    try:
        action()
    except OSError:
        results[name] = True
    else:
        results[name] = False
results['source_read_control'] = (root / 'src/app.py').read_text() == 'old'
for name, path in [('source_write', 'src/app.py'), ('root_instruction', 'AGENTS.md'),
                   ('nested_instruction', 'src/AGENTS.md'), ('hardlink_alias', 'alias'),
                   ('symlink_alias', 'link'), ('new_instruction', 'src/CLAUDE.md')]:
    denied(name, lambda path=path: (root / path).write_text('attacked'))
denied('new_parent_directory', lambda: (root / 'new').mkdir())
denied('rename_parent', lambda: (root / 'src').rename(root / 'moved'))
denied('unlink_instruction', lambda: (root / 'AGENTS.md').unlink())
denied('hardlink_create', lambda: os.link(root / 'AGENTS.md', '/tmp/alias'))
denied('proc_root_alias', lambda: pathlib.Path('/proc/self/root/workspace/AGENTS.md').write_text('attacked'))
pathlib.Path('/tmp/instruction-link').symlink_to('/workspace/AGENTS.md')
denied('scratch_symlink_alias', lambda: pathlib.Path('/tmp/instruction-link').write_text('attacked'))
denied('host_credential_file', lambda: pathlib.Path(config['secret_path']).read_text())
denied('host_capture_file', lambda: pathlib.Path(config['capture_path']).write_text('attacked'))
results['credential_environment'] = not any(k in os.environ for k in ['AGENT_PAT', 'OPENAI_API_KEY', 'UNUSUAL_CANARY', 'BASH_ENV', 'LD_PRELOAD'])
results['synthetic_home'] = os.environ['HOME'] == '/home/worker' and not list(pathlib.Path('/home/worker').iterdir())
denied('home_config_creation', lambda: pathlib.Path('/home/worker/.codex').mkdir())
results['nested_user_namespace_denied'] = subprocess.run(['/usr/bin/unshare', '-Ur', '/bin/true'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode != 0
results['inherited_fd'] = not pathlib.Path('/proc/self/fd/' + str(config['secret_fd'])).exists()
# Inspect only synthetic marker matches, never print another process environment.
results['host_process_credentials'] = True
for p in pathlib.Path('/proc').glob('[0-9]*/environ'):
    try:
        if config['canary'].encode() in p.read_bytes():
            results['host_process_credentials'] = False
    except OSError:
        pass
for kind in ['tcp', 'abstract_unix']:
    sock = socket.socket(socket.AF_INET if kind == 'tcp' else socket.AF_UNIX)
    sock.settimeout(.5)
    destination = ('127.0.0.1', config['port']) if kind == 'tcp' else '\0' + config['socket_name']
    denied('host_' + kind, lambda: sock.connect(destination))
    sock.close()
# Prove a useful test can run, with scratch writable and source still read-only.
pathlib.Path('/tmp/build-output').write_text('scratch')
results['test_scratch_control'] = pathlib.Path('/tmp/build-output').read_text() == 'scratch'
# Deliberate negative control: this sandbox is not a command allow-list.
results['arbitrary_shell_available_negative_control'] = subprocess.run(['/bin/sh', '-c', 'exit 0']).returncode == 0
print(json.dumps(results))
'''


def main():
    root = Path(tempfile.mkdtemp(prefix='codex-broker-proof-'))
    source, fixture = root / 'source', root / 'fixture'
    source.mkdir()
    fixture.mkdir()
    (source / 'src').mkdir()
    (source / 'src/app.py').write_text('old')
    (source / 'src/AGENTS.md').write_text('nested protected')
    (source / 'AGENTS.md').write_text('protected')
    os.link(source / 'AGENTS.md', source / 'alias')
    (source / 'link').symlink_to('AGENTS.md')
    secret = root / 'synthetic-secret'
    secret.write_text('synthetic credential only')
    capture = root / 'capture'
    capture.write_text('harness capture')
    (fixture / 'check.py').write_text(CHECK)
    canary = 'synthetic-' + uuid.uuid4().hex
    checks = {}
    with socket.socket() as listener, socket.socket(socket.AF_UNIX) as unix_listener:
        listener.bind(('127.0.0.1', 0))
        listener.listen()
        socket_name = 'broker-probe-' + uuid.uuid4().hex
        unix_listener.bind('\0' + socket_name)
        unix_listener.listen()
        with socket.create_connection(listener.getsockname()):
            checks['host_tcp_positive_control'] = True
        with socket.socket(socket.AF_UNIX) as control:
            control.connect('\0' + socket_name)
            checks['host_unix_positive_control'] = True
        fd = os.open(secret, os.O_RDONLY)
        os.set_inheritable(fd, True)
        # Deliberately expose a canary in a sibling host process, never real auth.
        sibling = subprocess.Popen(['/usr/bin/sleep', '30'],
                                   env={'UNUSUAL_CANARY': canary}, close_fds=True)
        originals = {key: os.environ.get(key) for key in
                     ['AGENT_PAT', 'OPENAI_API_KEY', 'UNUSUAL_CANARY']}
        try:
            os.environ.update({key: canary for key in originals})
            (fixture / 'probe.json').write_text(json.dumps(dict(
                secret_path=str(secret), capture_path=str(capture), secret_fd=fd,
                canary=canary, port=listener.getsockname()[1], socket_name=socket_name)))
            checks['host_environment_positive_control'] = canary.encode() in Path(f'/proc/{sibling.pid}/environ').read_bytes()
            checks['host_fd_positive_control'] = os.read(fd, 100) == b'synthetic credential only'
            run = Commands(source, fixture).request({'op': 'test'})
        finally:
            for key, value in originals.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
            os.close(fd)
            sibling.terminate()
            sibling.wait(timeout=2)
    checks['sandbox_started'] = run['exit_code'] == 0 and not run['timed_out']
    if checks['sandbox_started']:
        checks.update(json.loads(run['stdout']))
    checks['host_instruction_unchanged'] = (source / 'AGENTS.md').read_text() == 'protected'
    checks['host_nested_instruction_unchanged'] = (source / 'src/AGENTS.md').read_text() == 'nested protected'
    checks['host_capture_unchanged'] = capture.read_text() == 'harness capture'
    # A broker mutation is visible in a fresh worker mount; no direct writes.
    broker = Broker(source, 'IMPLEMENT')
    try:
        broker.request(dict(op='put', path='src/app.py', content='broker edit', expected=digest(b'old')))
    finally:
        broker.close()
    edit_read = run_sandbox(source, fixture, ['/usr/bin/cat', '/workspace/src/app.py'])
    checks['broker_edit_visible_control'] = edit_read['exit_code'] == 0 and edit_read['stdout'] == 'broker edit'
    # Escape a process group with setsid. PID namespace lifetime must still stop it.
    marker = 'broker-descendant-' + uuid.uuid4().hex
    daemon_code = 'import time; print("descendant-ready", flush=True); time.sleep(60) # ' + marker
    (fixture / 'daemon.py').write_text(
        'import subprocess,time\n'
        f'subprocess.Popen(["/usr/bin/python3", "-I", "-c", {daemon_code!r}], start_new_session=True)\n'
        'print("descendant-started", flush=True)\ntime.sleep(60)\n')
    cancelled = run_sandbox(source, fixture, ['/usr/bin/python3', '-I', '/fixture/daemon.py'], timeout=1)
    checks['timeout_observed'] = cancelled['timed_out'] and 'descendant-ready' in cancelled['stdout']
    # Allow kernel process teardown, ignoring zombies (no executable process left).
    def descendant_alive():
        for path in Path('/proc').glob('[0-9]*/cmdline'):
            try:
                if marker.encode() in path.read_bytes():
                    return True
            except OSError:
                pass
        return False
    deadline = time.monotonic() + 2
    while descendant_alive() and time.monotonic() < deadline:
        time.sleep(.05)
    checks['setsid_descendant_stopped'] = not descendant_alive()
    report = dict(prototype_only=True, codex_enabled=False,
                  fixture_root=str(root), checks=checks, all_observations_pass=all(checks.values()),
                  sandbox_error=run['stderr'],
                  boundary_limits=['No actual Codex tool routing or authentication tested',
                                   'Arbitrary shell negative control is expected to succeed',
                                   'Synthetic source export only; no production credential inventory'])
    print(json.dumps(report, indent=2))
    return 0 if all(checks.values()) else 1


if __name__ == '__main__':
    raise SystemExit(main())

import errno
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile

root = Path(tempfile.mkdtemp(prefix='codex-runner-boundaries-'))
work = root / 'workspace'
work.mkdir()
(work / '.agent-data').mkdir()
(work / 'source.txt').write_text('original')
for name in ['AGENTS.md', 'CLAUDE.md', '.agents/policy.txt', '.codex/policy.txt', '.claude/policy.txt']:
    p = work / name
    p.parent.mkdir(exist_ok=True)
    p.write_text('protected')
for name in ['memory.txt', 'capture.txt', 'fake-credential.txt']:
    (root / name).write_text('fixture-only')
(work / 'memory-link').symlink_to(root / 'memory.txt')
(work / 'policy-link').symlink_to(work / 'AGENTS.md')

settings = ('permissions.sp-proof={filesystem={":root"="read", '
    + json.dumps(str(root / 'fake-credential.txt')) + '="deny", '
    '":workspace_roots"={"."="write","AGENTS.md"="read","CLAUDE.md"="read",'
    '".agents"="read",".codex"="read",".claude"="read"}},network={enabled=false}}')
triage = ('permissions.sp-triage={filesystem={":root"="read", '
    '":workspace_roots"={"."="read",".agent-data"="write"}},network={enabled=false}}')
results = []

def run(name, code, profile='sp-proof'):
    args = ['codex', 'sandbox', '-P', profile, '-C', str(work)]
    if profile == 'sp-proof': args += ['-c', settings]
    if profile == 'sp-triage': args += ['-c', triage]
    cp = subprocess.run(args + ['/usr/bin/python3', '-c', code], text=True, capture_output=True, timeout=20)
    item = dict(name=name, passed=cp.returncode == 0, exit_code=cp.returncode)
    if cp.returncode: item['diagnostic'] = (cp.stderr + cp.stdout)[-2000:]
    results.append(item)
    print(json.dumps(item), flush=True)

def denied_write(path):
    return f'''from pathlib import Path
import errno
try:
    Path({str(path)!r}).write_text('FORBIDDEN')
except OSError as e:
    assert e.errno in (errno.EACCES, errno.EPERM, errno.EROFS), e
else:
    raise AssertionError('forbidden write succeeded')
'''

run('read-only source read', "from pathlib import Path; assert Path('source.txt').read_text() == 'original'", ':read-only')
run('read-only source write denied', denied_write(work / 'source.txt'), ':read-only')
run('read-only new file denied', denied_write(work / 'new.txt'), ':read-only')
run('implementation source edit allowed', "from pathlib import Path; Path('source.txt').write_text('allowed'); assert Path('source.txt').read_text() == 'allowed'")
run('triage artifact write allowed', "from pathlib import Path; Path('.agent-data/plan.md').write_text('plan')", 'sp-triage')
run('triage source write denied', denied_write(work / 'source.txt'), 'sp-triage')
for name in ['AGENTS.md','CLAUDE.md','.agents/policy.txt','.codex/policy.txt','.claude/policy.txt','memory-link','policy-link']:
    run('protected write denied: '+name, denied_write(work / name))
for name in ['memory.txt','capture.txt']:
    run('outside write denied: '+name, denied_write(root / name))
run('external memory readable', f"from pathlib import Path; assert Path({str(root / 'memory.txt')!r}).read_text() == 'fixture-only'")
run('synthetic credential unreadable', f'''from pathlib import Path
import errno
try:
    Path({str(root / 'fake-credential.txt')!r}).read_text()
except OSError as e:
    assert e.errno in (errno.EACCES, errno.EPERM), e
else:
    raise AssertionError('credential readable')
''')
# A real listening local socket distinguishes sandbox refusal from absent service.
with socket.socket() as listener:
    listener.bind(('127.0.0.1', 0))
    listener.listen(3)
    port = listener.getsockname()[1]
    with socket.create_connection(('127.0.0.1', port), timeout=2): pass
    run('network denied to reachable local listener', f'''import socket, errno
try:
    socket.create_connection(('127.0.0.1', {port}), timeout=2)
except OSError as e:
    assert e.errno in (errno.EACCES, errno.EPERM), e
else:
    raise AssertionError('network connection allowed')
''')
# Independently check that denied operations did not corrupt fixtures.
assert (work/'source.txt').read_text() == 'allowed'
assert (work/'AGENTS.md').read_text() == 'protected'
assert (root/'memory.txt').read_text() == 'fixture-only'
assert (root/'capture.txt').read_text() == 'fixture-only'
report = dict(fixture_root=str(root), results=results)
Path('/tmp/codex-runner-boundary-results.json').write_text(json.dumps(report, indent=2)+'\n')
raise SystemExit(0 if all(x['passed'] for x in results) else 1)

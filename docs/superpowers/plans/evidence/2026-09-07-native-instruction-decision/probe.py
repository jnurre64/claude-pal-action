#!/usr/bin/env python3
"""No-model component probe. Writes only fresh /tmp fixtures; no host policy changes."""
import argparse
import json
import os
from pathlib import Path
import shlex
import signal
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('srt', type=Path)
    parser.add_argument('--baseline', action='store_true', help='unconfined fixture controls only')
    args = parser.parse_args()
    srt = args.srt.resolve(strict=True)
    root = Path(tempfile.mkdtemp(prefix='sp116-native-instructions-'))
    cases = {
        'source_edit': ('Path("source.txt").write_text("changed")', False),
        'instruction_read': ('assert Path("AGENTS.md").read_text() == "original"', False),
        'root_write': ('Path("AGENTS.md").write_text("changed")', True),
        'nested_write': ('Path("nested/Claude.md").write_text("changed")', True),
        'symlink_write': ('Path("symbol.txt").write_text("changed")', True),
        'hardlink_write': ('Path("alias.txt").write_text("changed")', True),
        'root_unlink': ('Path("AGENTS.md").unlink()', True),
        'parent_replacement': ('Path("nested").rename("moved"); Path("nested").mkdir(); Path("nested/Claude.md").write_text("changed")', True),
        'new_instruction': ('Path("fresh").mkdir(); Path("fresh/Agents.md").write_text("changed")', True),
        'new_source_directory': ('Path("fresh").mkdir(); Path("fresh/source.txt").write_text("changed")', False),
    }
    results = []
    for name, (operation, should_deny) in cases.items():
        case = root / name
        workspace = case / 'workspace'
        home = case / 'home'
        workspace.mkdir(parents=True)
        home.mkdir()
        (workspace / 'nested').mkdir()
        for file in ('AGENTS.md', 'nested/Claude.md', 'source.txt'):
            (workspace / file).write_text('original')
        os.link(workspace / 'AGENTS.md', workspace / 'alias.txt')
        (workspace / 'symbol.txt').symlink_to('AGENTS.md')
        # Literal exact denies are the documented Linux mechanism. Protect all
        # known instruction names, including the existing mixed-case path.
        settings = {'filesystem': {'allowWrite': [str(workspace)], 'denyRead': [],
                    'denyWrite': [str(workspace / 'AGENTS.md'), str(workspace / 'nested/Claude.md')]},
                    'network': {'allowedDomains': [], 'deniedDomains': []}}
        config = case / 'settings.json'
        config.write_text(json.dumps(settings))
        code = 'from pathlib import Path\nimport json\nprint("PROBE_STARTED", flush=True)\ntry:\n ' + operation + '\n print(json.dumps({"operation_allowed": True}))\nexcept OSError as e:\n print(json.dumps({"operation_allowed": False, "errno": e.errno}))\n'
        command = '/usr/bin/python3 -c ' + shlex.quote(code)
        env = {'PATH': os.environ['PATH'], 'HOME': str(home), 'TMPDIR': str(case), 'LANG': 'C.UTF-8'}
        argv = ['/bin/bash', '-c', command] if args.baseline else [str(srt), '--settings', str(config), '-c', command]
        process = subprocess.Popen(argv, cwd=workspace,
                                   env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   text=True, start_new_session=True)
        try:
            stdout, stderr = process.communicate(timeout=20)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            stdout, stderr = process.communicate()
        finally:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        parsed = None
        for line in stdout.splitlines():
            if line.startswith('{'):
                parsed = json.loads(line)
        started = 'PROBE_STARTED' in stdout and parsed is not None and process.returncode == 0
        root_unchanged = (workspace / 'AGENTS.md').is_file() and (workspace / 'AGENTS.md').read_text() == 'original'
        nested_unchanged = (workspace / 'nested/Claude.md').is_file() and (workspace / 'nested/Claude.md').read_text() == 'original'
        new_absent = not (workspace / 'fresh/Agents.md').exists()
        matched = started and (parsed['operation_allowed'] if args.baseline else parsed['operation_allowed'] != should_deny)
        if should_deny and not args.baseline:
            matched = matched and root_unchanged and nested_unchanged and new_absent
        results.append({'case': name, 'expected_denied': should_deny, 'started': started,
                        'observation': parsed, 'root_unchanged': root_unchanged,
                        'nested_unchanged': nested_unchanged, 'new_instruction_absent': new_absent,
                        'matched': matched, 'exit_code': process.returncode, 'stderr': stderr})
    print(json.dumps({'fixture': str(root), 'component': str(srt), 'baseline': args.baseline, 'results': results}, indent=2))
    if not all(row['started'] for row in results):
        return 2
    return 0 if all(row['matched'] for row in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())

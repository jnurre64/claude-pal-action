#!/usr/bin/env python3
"""Actual CLI + production shell adapter, canned loopback responses, no inference."""
import http.server
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[5]


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        self.server.requests.append({'model': body.get('model'), 'schema': body.get('text'),
                                     'input_count': len(body.get('input', []))})
        def strict_objects(node):
            if not isinstance(node, dict):
                return True
            if node.get('type') == 'object':
                if node.get('additionalProperties') is not False or set(node.get('required', [])) != set(node.get('properties', {})):
                    return False
            return all(strict_objects(value) if isinstance(value, dict) else
                       all(strict_objects(item) for item in value) if isinstance(value, list) else True
                       for value in node.values())
        native = body.get('text', {}).get('format', {}).get('schema', {})
        if not strict_objects(native):
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"error":{"message":"Fixture: strict object schema required"}}')
            return
        if self.server.mode == 'quota':
            self.send_response(429)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"error":{"message":"Fixture quota exhausted","type":"insufficient_quota","code":"insufficient_quota"}}')
            return
        if self.server.mode == 'timeout':
            time.sleep(4)
        text = self.server.answer
        item = {'id': 'msg_fixture', 'type': 'message', 'role': 'assistant', 'status': 'completed',
                'content': [{'type': 'output_text', 'text': text, 'annotations': []}]}
        response = {'id': 'resp_fixture', 'object': 'response', 'status': 'completed', 'output': [item],
                    'usage': {'input_tokens': 7, 'output_tokens': 3, 'total_tokens': 10}}
        events = [{'type': 'response.created', 'response': dict(response, status='in_progress', output=[])},
                  {'type': 'response.output_item.added', 'output_index': 0, 'item': dict(item, status='in_progress', content=[])},
                  {'type': 'response.content_part.added', 'item_id': 'msg_fixture', 'output_index': 0, 'content_index': 0,
                   'part': {'type': 'output_text', 'text': '', 'annotations': []}},
                  {'type': 'response.output_text.delta', 'item_id': 'msg_fixture', 'output_index': 0, 'content_index': 0, 'delta': text},
                  {'type': 'response.output_item.done', 'output_index': 0, 'item': item},
                  {'type': 'response.completed', 'response': response}]
        try:
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.end_headers()
            self.wfile.write(''.join('data: ' + json.dumps(event) + '\n\n' for event in events).encode())
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass


def main():
    root = Path(tempfile.mkdtemp(prefix='sp116-cli-integration-'))
    codex = Path(shutil.which('codex')).resolve(strict=True)
    python = Path(shutil.which('python3')).absolute()
    shell = r'''
set -euo pipefail
SCRIPT_DIR="$RUNTIME/scripts"
EVENT_TYPE="$EVENT"
NUMBER=116
source "$RUNTIME/scripts/lib/defaults.sh"
source "$RUNTIME/scripts/lib/common.sh"
agent_preflight_dispatch "$EVENT"
run_agent 'Return the fixture response; do not call tools.' "$AGENT_ALLOWED_TOOLS_TRIAGE" '' '' "$PHASE"
'''
    cases = [('review', 'POST_IMPL_REVIEW', 'implement', '{"action":"approved","verified_fixed":[],"reopened":[],"findings":[]}'),
             ('triage', 'TRIAGE', 'new_issue', json.dumps({'action': 'plan_ready', 'questions': [], 'summary': 'Offline plan', 'plan_markdown': '## Implementation Plan\n\nOffline CLI plan.'})),
             ('invalid_schema', 'POST_IMPL_REVIEW', 'implement', '{"action":"not-valid"}'),
             ('quota', 'POST_IMPL_REVIEW', 'implement', ''),
             ('timeout', 'POST_IMPL_REVIEW', 'implement', 'late')]
    results = []
    for mode, phase, event, answer in cases:
        case = root / mode
        workspace, home, config, logs, binary = [case / name for name in ('workspace', 'home', 'codex-home', 'logs', 'bin')]
        for path in (workspace, home, config, logs, binary):
            path.mkdir(parents=True)
        (binary / 'codex').symlink_to(codex)
        subprocess.run(['git', 'init', '-q', str(workspace)], check=True)
        (workspace / 'source.txt').write_text('original')
        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        server.requests, server.mode, server.answer = [], mode, answer
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        (config / 'config.toml').write_text(f'''
model_provider = "fixture"
model = "offline-fixture"
web_search = "disabled"
[features]
enable_request_compression = false
[model_providers.fixture]
name = "Offline fixture"
base_url = "http://127.0.0.1:{server.server_port}/v1"
wire_api = "responses"
requires_openai_auth = false
supports_websockets = false
request_max_retries = 0
stream_max_retries = 0
''')
        env = {'PATH': str(binary) + ':' + str(python.parent) + ':/usr/bin:/bin', 'HOME': str(home), 'CODEX_HOME': str(config),
               'LANG': 'C.UTF-8', 'CODEX_API_KEY': 'synthetic-fixture-only', 'RUNTIME': str(ROOT),
               'WORKTREE_DIR': str(workspace), 'AGENT_LOG_DIR': str(logs), 'AGENT_ENGINE': 'codex',
               'AGENT_TIMEOUT': '1' if mode == 'timeout' else '15',
               'AGENT_EXECUTION_MODE': 'orchestrator', 'AGENT_BOT_USER': 'fixture', 'PHASE': phase, 'EVENT': event}
        completed = subprocess.run(['/bin/bash', '-c', shell], env=env, cwd=workspace,
                                   capture_output=True, text=True, timeout=30)
        server.shutdown()
        server.server_close()
        try:
            envelope = json.loads(completed.stdout)
        except ValueError:
            envelope = None
        plan = workspace / '.agent-data/plan.md'
        results.append({'case': mode, 'exit_code': completed.returncode, 'envelope': envelope,
                        'stderr': completed.stderr, 'requests': server.requests,
                        'plan': plan.read_text() if plan.exists() else None,
                        'source_unchanged': (workspace / 'source.txt').read_text() == 'original',
                        'capture_files': sorted(p.name for p in logs.glob('codex-*/*'))})
    expected = {'review': ('success', None), 'triage': ('success', None),
                'invalid_schema': ('failed', 'schema'), 'quota': ('failed', 'quota'),
                'timeout': ('timed_out', 'transport')}
    for row in results:
        envelope = row['envelope'] or {}
        status, error = expected[row['case']]
        row['passed'] = (row['exit_code'] == 0 and envelope.get('engine') == 'codex'
                         and envelope.get('status') == status
                         and (envelope.get('error') or {}).get('kind') == error
                         and len(row['requests']) == 1 and row['source_unchanged']
                         and row['capture_files'] == ['result.json', 'stderr.log'])
        if row['case'] == 'triage':
            row['passed'] = (row['passed'] and row['plan'] == '## Implementation Plan\n\nOffline CLI plan.'
                             and 'plan_markdown' not in envelope['structured_output']
                             and 'plan_markdown' in row['requests'][0]['schema']['format']['schema']['properties'])
        else:
            row['passed'] = row['passed'] and row['plan'] is None
        if status == 'success':
            row['passed'] = row['passed'] and envelope.get('schema_status') == 'valid'
            row['passed'] = row['passed'] and envelope.get('usage', {}).get('input_tokens') == 7
    passed = all(row['passed'] for row in results)
    print(json.dumps({'fixture': str(root), 'codex': str(codex), 'all_passed': passed, 'results': results}, indent=2))
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())

"""Inspect actual CLI tool inventory with a local canned Responses server.

The fake server and CLI both run inside the external, network-isolated sandbox.
No model inference or credentials. Tool inventory is NOT tool-call enforcement.
"""
import json
from pathlib import Path
import shutil
import tempfile

from prototype import run_sandbox

CHILD = r'''
import http.server, json, os, pathlib, subprocess, threading
requests = []
class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        requests.append(body)
        item = {'id':'msg_fixture', 'type':'message', 'role':'assistant', 'status':'completed', 'content':[{'type':'output_text','text':'Offline fixture complete.','annotations':[]}]}
        response = {'id':'resp_fixture','object':'response','status':'completed','output':[item], 'usage':{'input_tokens':1,'output_tokens':1,'total_tokens':2}}
        events = [
            {'type':'response.created','response':dict(response,status='in_progress',output=[])},
            {'type':'response.output_item.added','output_index':0,'item':dict(item,status='in_progress',content=[])},
            {'type':'response.content_part.added','item_id':'msg_fixture','output_index':0,'content_index':0,'part':{'type':'output_text','text':'','annotations':[]}},
            {'type':'response.output_text.delta','item_id':'msg_fixture','output_index':0,'content_index':0,'delta':'Offline fixture complete.'},
            {'type':'response.output_item.done','output_index':0,'item':item},
            {'type':'response.completed','response':response}]
        self.send_response(200)
        self.send_header('Content-Type','text/event-stream')
        self.end_headers()
        self.wfile.write(''.join('data: '+json.dumps(e)+'\n\n' for e in events).encode())
        self.wfile.flush()
server = http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
threading.Thread(target=server.serve_forever,daemon=True).start()
results = []
for restricted in [False, True]:
    requests.clear()
    home = '/tmp/codex-home-' + str(restricted)
    pathlib.Path(home).mkdir()
    command = ['/fixture/codex','exec','--ignore-user-config','--ignore-rules',
               '--skip-git-repo-check','--ephemeral','--json','-C','/workspace',
               '-c','model="offline-fixture"', '-c','model_provider="fixture"',
               '-c','model_providers.fixture.name="Offline fixture"',
               '-c',f'model_providers.fixture.base_url="http://127.0.0.1:{server.server_port}/v1"',
               '-c','model_providers.fixture.wire_api="responses"',
               '-c','model_providers.fixture.requires_openai_auth=false',
               '-c','model_providers.fixture.supports_websockets=false',
               '-c','features.enable_request_compression=false',
               '-c','approval_policy="never"', '-c','web_search="disabled"']
    if restricted:
        for feature in ['shell_tool','unified_exec','hooks','plugins','apps','multi_agent',
                        'browser_use','computer_use','image_generation','code_mode_host']:
            command += ['--disable',feature]
    command += ['Return the exact text: Offline fixture complete.']
    try:
        completed = subprocess.run(command,env={'PATH':'/usr/bin:/bin','HOME':'/home/worker',
                                   'CODEX_HOME':home,'LANG':'C.UTF-8'},capture_output=True,text=True,timeout=20)
    except subprocess.TimeoutExpired:
        results.append({'restricted':restricted,'timed_out':True})
        continue
    def names(tools):
        result=[]
        for tool in tools:
            result.append({'type':tool.get('type'),'name':tool.get('name') or tool.get('function',{}).get('name')})
            if tool.get('tools'):
                result.extend(names(tool['tools']))
        return result
    events = [json.loads(line) for line in completed.stdout.splitlines() if line.startswith('{')]
    results.append({'restricted':restricted,'exit_code':completed.returncode,
                    'request_count':len(requests),'tools':names(requests[0].get('tools',[])) if requests else [],
                    'terminal_success':any(e.get('type') == 'turn.completed' for e in events),
                    'stderr':completed.stderr[-4000:]})
server.shutdown()
print(json.dumps(results))
'''


def main():
    root = Path(tempfile.mkdtemp(prefix='codex-broker-tools-'))
    source, fixture = root / 'source', root / 'fixture'
    source.mkdir()
    fixture.mkdir()
    (source / 'AGENTS.md').write_text('Offline fixture. Return the requested text.')
    (fixture / 'tools.py').write_text(CHILD)
    # Private copy avoids exposing the installation or personal CODEX_HOME.
    binary = Path(shutil.which('codex')).resolve()
    shutil.copy2(binary, fixture / 'codex')
    result = run_sandbox(source, fixture, ['/usr/bin/python3','-I','/fixture/tools.py'], timeout=50)
    report = {'prototype_only':True,'codex_enabled':False,'fixture_root':str(root),
              'sandbox_exit_code':result['exit_code'],'sandbox_stderr':result['stderr'],
              'observations':json.loads(result['stdout']) if result['exit_code'] == 0 else [],
              'limit':'Tool advertisement only; no model-driven tool call or authentication proof'}
    observations = report['observations']
    passed = result['exit_code'] == 0 and len(observations) == 2 and all(
        o.get('exit_code') == 0 and o.get('terminal_success')
        and o.get('request_count') == 1 for o in observations)
    if passed:
        baseline = {t['name'] for t in observations[0]['tools']}
        restricted = {t['name'] for t in observations[1]['tools']}
        passed = ({'exec_command', 'write_stdin', 'spawn_agent'} <= baseline
                  and restricted == {'request_user_input', 'view_image'})
    report['all_observations_pass'] = passed
    print(json.dumps(report,indent=2))
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())

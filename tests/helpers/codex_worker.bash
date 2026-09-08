_codex_worker() {
    mkdir -p "$TEST_TEMP_DIR/bin" "$TEST_TEMP_DIR/home"
    export PATH="$TEST_TEMP_DIR/bin:$PATH" HOME="$TEST_TEMP_DIR/home"
    unset CODEX_API_KEY
    export MOCK_CODEX_MODE=success MOCK_AUTH_EXIT=0
    cat > "$TEST_TEMP_DIR/bin/codex" <<'PY'
#!/usr/bin/env python3
import json, os, pathlib, signal, subprocess, sys, time
root=pathlib.Path(os.environ['TEST_TEMP_DIR'])
args=sys.argv[1:]
if args==['exec','--help']:
    print('--json --output-last-message --output-schema --sandbox --ephemeral' if os.environ['MOCK_CODEX_MODE']!='old' else 'old CLI')
    raise SystemExit(0)
if args==['login','status']:
    (root/'auth-called').touch()
    print('synthetic identity must not be printed',file=sys.stderr)
    raise SystemExit(int(os.environ['MOCK_AUTH_EXIT']))
prompt=sys.stdin.read()
(root/'invocation.json').write_text(json.dumps({'argv':args,'prompt':prompt,'cwd':os.getcwd(),'home':os.environ['HOME']}))
mode=os.environ['MOCK_CODEX_MODE']
if mode in ('hang','child'):
    child=subprocess.Popen([sys.executable,'-c',"import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); time.sleep(60)"])
    (root/'child-pid').write_text(str(child.pid))
    if mode=='hang':
        signal.signal(signal.SIGTERM,signal.SIG_IGN)
        time.sleep(60)
text='{"verdict":"approved"}' if '--output-schema' in args else 'done'
if '--output-schema' in args and 'action' in json.loads(pathlib.Path(args[args.index('--output-schema')+1]).read_text()).get('properties',{}):
    text=json.dumps({'action':'approved','verified_fixed':[],'reopened':[],'findings':[]})
if '--output-schema' in args and 'plan_markdown' in json.loads(pathlib.Path(args[args.index('--output-schema')+1]).read_text()).get('properties',{}):
    text=os.environ.get('MOCK_TRIAGE_OUTPUT',json.dumps({'action':'plan_ready','plan_markdown':'## Implementation Plan\n\nTested plan.'}))
final=pathlib.Path(args[args.index('--output-last-message')+1])
if mode!='missing':
    final.write_text(text+'\n')
for event in [{'type':'thread.started','thread_id':'mock'}, {'type':'turn.started'}, {'type':'item.completed','item':{'type':'agent_message','text':text}}, {'type':'turn.completed'}]:
    print(json.dumps(event))
print(os.environ.get('WORKER_TEST_SECRET','mock diagnostic'),file=sys.stderr)
raise SystemExit(1 if mode=='failed' else 0)
PY
    chmod +x "$TEST_TEMP_DIR/bin/codex"
    jq -cn --arg worktree "$WORKTREE_DIR" --arg capture "$AGENT_LOG_DIR" \
        '{phase:"POST_IMPL_REVIEW",prompt:"review this\n$(do not execute)",model:"",schema_json:"",worktree:$worktree,capture_root:$capture,sandbox:"read-only",timeout:10}' > "$TEST_TEMP_DIR/request"
}

_invoke_codex_worker() {
    python3 "$LIB_DIR/codex-worker.py" run < "$TEST_TEMP_DIR/request"
}

_child_stopped() {
    python3 - "$TEST_TEMP_DIR/child-pid" <<'PY'
import pathlib,sys,time
pid=pathlib.Path(sys.argv[1]).read_text()
for _ in range(100):
    path=pathlib.Path('/proc')/pid/'stat'
    if not path.exists() or path.read_text().split()[2]=='Z':
        raise SystemExit(0)
    time.sleep(.01)
raise SystemExit(1)
PY
}

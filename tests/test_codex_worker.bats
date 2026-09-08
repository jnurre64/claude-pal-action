#!/usr/bin/env bats
load 'helpers/test_helper'

load 'helpers/codex_worker'

@test "codex worker: stdin prompt, normal home and native review argv produce one envelope" {
    _codex_worker
    run _invoke_codex_worker
    assert_success
    [ "${#lines[@]}" -eq 1 ]
    echo "$output" | jq -e '.engine == "codex" and .status == "success"'
    jq -e --arg home "$HOME" --arg cwd "$WORKTREE_DIR" '.home == $home and .cwd == $cwd and .prompt == "review this\n$(do not execute)" and (.argv | index("--ephemeral") != null) and (.argv | index("read-only") != null) and (.argv | index("approval_policy=\"never\"") != null) and (.argv | index("--ignore-user-config") == null) and (.argv | index("--ignore-rules") == null)' "$TEST_TEMP_DIR/invocation.json"
    [ -f "$TEST_TEMP_DIR/auth-called" ]
}

@test "codex worker: schema, opaque model, effort, persistence and writable paths use native options" {
    _codex_worker
    jq '. + {schema_json:"{\"type\":\"object\",\"properties\":{\"verdict\":{\"type\":\"string\"}},\"required\":[\"verdict\"]}",model:"custom model",effort:"high",persist:true,sandbox:"workspace-write",add_dirs:["/tmp/path with spaces"]}' "$TEST_TEMP_DIR/request" > "$TEST_TEMP_DIR/next"
    mv "$TEST_TEMP_DIR/next" "$TEST_TEMP_DIR/request"
    run _invoke_codex_worker
    echo "$output" | jq -e '.status == "success" and .schema_status == "valid" and .structured_output.verdict == "approved"'
    jq -e '.argv | index("--model=custom model") != null and index("--ephemeral") == null and index("/tmp/path with spaces") != null and index("model_reasoning_effort=\"high\"") != null' "$TEST_TEMP_DIR/invocation.json"
}

@test "codex worker: unsupported CLI or missing auth stops before execution without identity output" {
    _codex_worker
    MOCK_CODEX_MODE=old
    run _invoke_codex_worker
    echo "$output" | jq -e '.error.kind == "configuration" and .process_exit_code == null'
    [ ! -f "$TEST_TEMP_DIR/invocation.json" ]
    MOCK_CODEX_MODE=success MOCK_AUTH_EXIT=1
    run _invoke_codex_worker
    refute_output --partial 'synthetic identity'
    echo "$output" | jq -e '.error.message | contains("authentication")'
    [ ! -f "$TEST_TEMP_DIR/invocation.json" ]
    export CODEX_API_KEY=synthetic-exec-key
    rm "$TEST_TEMP_DIR/auth-called"
    run _invoke_codex_worker
    echo "$output" | jq -e '.status == "success"'
    [ ! -f "$TEST_TEMP_DIR/auth-called" ]
}

@test "codex worker: invalid native policy, schema and in-worktree captures fail before launch" {
    _codex_worker
    cp "$TEST_TEMP_DIR/request" "$TEST_TEMP_DIR/original"
    for change in '.sandbox="danger-full-access"' '.timeout=0' '.schema_json="{broken"' '.capture_root=.worktree' '.add_dirs=["relative"]' '.allowed_tools="Read"' '.budget_usd=1'; do
        jq "$change" "$TEST_TEMP_DIR/original" > "$TEST_TEMP_DIR/request"
        run _invoke_codex_worker
        assert_success
        echo "$output" | jq -e '.error.kind == "configuration"'
        [ ! -f "$TEST_TEMP_DIR/invocation.json" ]
    done
}

@test "codex worker: unique captures retain scrubbed results and diagnostics only" {
    _codex_worker
    export WORKER_TEST_SECRET='synthetic-secret-12345'
    run _invoke_codex_worker
    run _invoke_codex_worker
    python3 - "$AGENT_LOG_DIR" <<'PY'
import os,pathlib,stat,sys
dirs=list(pathlib.Path(sys.argv[1]).iterdir())
assert len(dirs)==2
for d in dirs:
    assert stat.S_IMODE(d.stat().st_mode)==0o700
    assert {p.name for p in d.iterdir()}=={'result.json','stderr.log'}
    assert '[REDACTED:WORKER_TEST_SECRET]' in (d/'stderr.log').read_text()
    assert all(os.environ['WORKER_TEST_SECRET'] not in p.read_text() for p in d.iterdir())
PY
}

@test "codex worker: missing final and nonzero exit cannot approve from useful events" {
    _codex_worker
    MOCK_CODEX_MODE=missing
    run _invoke_codex_worker
    echo "$output" | jq -e '.status == "failed" and .error.kind == "transport"'
    MOCK_CODEX_MODE=failed
    run _invoke_codex_worker
    echo "$output" | jq -e '.status == "failed" and .process_exit_code == 1'
}

@test "codex worker: timeout stops a stubborn child before returning" {
    _codex_worker
    MOCK_CODEX_MODE=hang
    jq '.timeout=1' "$TEST_TEMP_DIR/request" > "$TEST_TEMP_DIR/next"
    mv "$TEST_TEMP_DIR/next" "$TEST_TEMP_DIR/request"
    run _invoke_codex_worker
    assert_success
    echo "$output" | jq -e '.status == "timed_out"'
    _child_stopped
}

@test "codex worker: successful leader cannot leave its process group running" {
    _codex_worker
    MOCK_CODEX_MODE=child
    run _invoke_codex_worker
    assert_success
    echo "$output" | jq -e '.status == "success"'
    _child_stopped
}

@test "codex worker: cancellation emits a cancelled envelope and stops its child" {
    _codex_worker
    MOCK_CODEX_MODE=hang
    run python3 - "$LIB_DIR/codex-worker.py" "$TEST_TEMP_DIR" <<'PY'
import json,pathlib,signal,subprocess,sys,time
root=pathlib.Path(sys.argv[2])
p=subprocess.Popen([sys.executable,sys.argv[1],'run'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
try:
    p.stdin.write((root/'request').read_text());p.stdin.close();p.stdin=None
    deadline=time.monotonic()+8
    while not (root/'child-pid').exists():
        assert p.poll() is None and time.monotonic()<deadline
        time.sleep(.01)
    p.send_signal(signal.SIGTERM)
    out,err=p.communicate(timeout=5)
    assert p.returncode==0,err
    result=json.loads(out)
    assert result['status']=='cancelled' and result['process_exit_code']==143,result
finally:
    if p.poll() is None:
        p.kill();p.wait()
PY
    assert_success
    _child_stopped
}

@test "codex worker: public selection uses the adapter and refuses unavailable authentication" {
    _codex_worker
    source "$LIB_DIR/common.sh"
    AGENT_ENGINE=codex
    MOCK_AUTH_EXIT=1
    run run_agent prompt Read '' '' POST_IMPL_REVIEW
    echo "$output" | jq -e '.status == "failed" and .error.kind == "configuration" and .process_exit_code == null'
    [ ! -f "$TEST_TEMP_DIR/invocation.json" ]
    run agent_preflight_dispatch implement
    assert_failure
    assert_output --partial 'Codex authentication is unavailable'
}

@test "REGRESSION v1.2.0: Codex wire schemas meet strict output requirements without changing Claude schemas" {
    run python3 - "$LIB_DIR/codex-worker.py" "$SCRIPTS_DIR/../schemas" <<'PY'
import json, pathlib, runpy, sys
from jsonschema import Draft202012Validator
worker = runpy.run_path(sys.argv[1])

def example(schema):
    assert 'type' in schema, 'Native structured output requires a declared type'
    if 'enum' in schema:
        return schema['enum'][0]
    kind = schema['type']
    if isinstance(kind, list):
        kind = next(t for t in kind if t != 'null')
    if kind == 'object':
        assert schema['additionalProperties'] is False
        assert set(schema['required']) == set(schema['properties'])
        return {key: example(child) for key, child in schema['properties'].items()}
    if kind == 'array':
        return [example(schema['items'])]
    if kind == 'string':
        return 'fixture'
    raise AssertionError(kind)

for path in pathlib.Path(sys.argv[2]).glob('*.json'):
    before = path.read_text()
    native = json.loads(worker['wire_schema'](before))
    value = example(native)
    Draft202012Validator(native).validate(value)
    Draft202012Validator(json.loads(before)).validate(value)
    assert path.read_text() == before
    value['undeclared_field'] = 'must be rejected on wire'
    assert not Draft202012Validator(native).is_valid(value)
# Disabling the public triage schema still needs a valid internal plan contract.
fallback = json.loads(worker['wire_schema'](worker['phase_schema']('TRIAGE', '')))
Draft202012Validator(fallback).validate(example(fallback))
PY
    assert_success
}

@test "REGRESSION v1.2.0: unsupported native schema fails before launching Codex" {
    _codex_worker
    jq '.schema_json="{\"type\":\"object\",\"required\":[\"undeclared\"]}"' "$TEST_TEMP_DIR/request" > "$TEST_TEMP_DIR/next"
    mv "$TEST_TEMP_DIR/next" "$TEST_TEMP_DIR/request"
    run _invoke_codex_worker
    echo "$output" | jq -e '.status == "failed" and .error.kind == "configuration" and .process_exit_code == null'
    [ ! -f "$TEST_TEMP_DIR/invocation.json" ]
}

@test "REGRESSION v1.2.0: Codex editing can access linked worktree Git metadata while advisory phases cannot" {
    _codex_worker
    git init "$TEST_TEMP_DIR/repository with spaces" >/dev/null
    git -C "$TEST_TEMP_DIR/repository with spaces" -c user.name=Test -c user.email=test@example.invalid commit --allow-empty -m baseline >/dev/null
    git -C "$TEST_TEMP_DIR/repository with spaces" worktree add -b fixture "$TEST_TEMP_DIR/linked worktree" >/dev/null
    jq --arg wt "$TEST_TEMP_DIR/linked worktree" '.worktree=$wt | .phase="IMPLEMENT" | .sandbox="workspace-write"' "$TEST_TEMP_DIR/request" > "$TEST_TEMP_DIR/next"
    mv "$TEST_TEMP_DIR/next" "$TEST_TEMP_DIR/request"
    run _invoke_codex_worker
    echo "$output" | jq -e '.status == "success"'
    local metadata common
    metadata=$(git -C "$TEST_TEMP_DIR/linked worktree" rev-parse --absolute-git-dir)
    common=$(git -C "$TEST_TEMP_DIR/linked worktree" rev-parse --path-format=absolute --git-common-dir)
    jq -e --arg metadata "$metadata" --arg common "$common" '.argv | index($metadata) != null and index($common) != null' "$TEST_TEMP_DIR/invocation.json"
    jq '.phase="POST_IMPL_REVIEW" | .sandbox="read-only"' "$TEST_TEMP_DIR/request" > "$TEST_TEMP_DIR/next"
    mv "$TEST_TEMP_DIR/next" "$TEST_TEMP_DIR/request"
    run _invoke_codex_worker
    echo "$output" | jq -e '.status == "success"'
    jq -e '.argv | index("--add-dir") == null' "$TEST_TEMP_DIR/invocation.json"
}

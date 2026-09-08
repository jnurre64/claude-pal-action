#!/usr/bin/env bats
load 'helpers/test_helper'

_codex_fixture() {
    export CODEX_TEXT='done' CODEX_EXIT=0 CODEX_SCHEMA=''
    export CODEX_MUTATION=''
    printf 'done\n' > "$TEST_TEMP_DIR/final"
    : > "$TEST_TEMP_DIR/stderr"
}

_codex_result() {
    python3 - <<'PY' > "$TEST_TEMP_DIR/events"
import json, os
events = [
    {"type": "thread.started", "thread_id": "fixture"},
    {"type": "turn.started"},
    {"type": "item.completed", "item": {"type": "agent_message", "text": os.environ["CODEX_TEXT"]}},
    {"type": "turn.completed", "usage": {"input_tokens": 7, "output_tokens": 3, "cached_input_tokens": 2}},
]
exec(os.environ["CODEX_MUTATION"])
for event in events:
    print(json.dumps(event))
PY
    python3 "$LIB_DIR/agent-result.py" normalize-codex POST_IMPL_REVIEW "$CODEX_EXIT" "$CODEX_SCHEMA" \
        "$TEST_TEMP_DIR/stderr" "$TEST_TEMP_DIR/final" < "$TEST_TEMP_DIR/events"
}

@test "codex result: native terminal result matches final capture and preserves unknown telemetry" {
    _codex_fixture
    run _codex_result
    assert_success
    [ "${#lines[@]}" -eq 1 ]
    echo "$output" | jq -e '.engine == "codex" and .phase == "POST_IMPL_REVIEW" and .status == "success" and .result_text == "done" and .usage.cached_input_tokens == 2 and .cost_usd == null and .denials_available == false'
}

@test "codex result: missing, duplicated, out-of-order and truncated events cannot succeed" {
    _codex_fixture
    for CODEX_MUTATION in 'events.pop()' 'events.append(events[-1])' 'events.reverse()' 'events.pop(0)' 'events.pop(1)' 'events.insert(2, events[1])' 'events.append([])' 'events=[]'; do
        run _codex_result
        assert_success
        echo "$output" | jq -e '.status == "failed" and .error.kind == "transport" and .structured_output == null'
    done
    run bash -c 'printf "{broken" | python3 "$1/agent-result.py" normalize-codex REVIEW 0 "" "$2/stderr" "$2/final"' _ "$LIB_DIR" "$TEST_TEMP_DIR"
    assert_success
    echo "$output" | jq -e '.error.kind == "transport"'
}

@test "codex result: absent or stale final capture cannot approve a review" {
    _codex_fixture
    printf 'old approved finding' > "$TEST_TEMP_DIR/final"
    run _codex_result
    echo "$output" | jq -e '.status == "failed" and .error.kind == "transport"'
    rm "$TEST_TEMP_DIR/final"
    run _codex_result
    assert_success
    echo "$output" | jq -e '.status == "failed" and .error.kind == "transport"'
}

@test "codex result: structured review requires final JSON satisfying the configured schema" {
    _codex_fixture
    CODEX_SCHEMA='{"type":"object","required":["verdict"],"properties":{"verdict":{"enum":["approved"]}},"additionalProperties":false}'
    for CODEX_TEXT in '{"verdict":"approved"}' '{"verdict":"wrong"}' 'not json'; do
        printf '%s\n' "$CODEX_TEXT" > "$TEST_TEMP_DIR/final"
        run _codex_result
        assert_success
        if [[ "$CODEX_TEXT" == *approved* ]]; then
            echo "$output" | jq -e '.schema_status == "valid" and .structured_output.verdict == "approved"'
        else
            echo "$output" | jq -e '.status == "failed" and .schema_status == "invalid" and .structured_output == null'
        fi
    done
}

@test "codex result: terminal failures override useful text and schema output at exit zero" {
    _codex_fixture
    CODEX_TEXT='{"verdict":"approved"}'
    CODEX_SCHEMA='{"type":"object"}'
    printf '%s' "$CODEX_TEXT" > "$TEST_TEMP_DIR/final"
    CODEX_MUTATION='events[-1] = {"type":"turn.failed", "error":{"message":"401 authentication failed"}}'
    run _codex_result
    echo "$output" | jq -e '.status == "failed" and .error.kind == "auth" and .structured_output == null and .process_exit_code == 0'
    CODEX_MUTATION='events.insert(2, {"type":"error", "message":"quota exhausted"})'
    run _codex_result
    echo "$output" | jq -e '.status == "failed" and .error.kind == "quota" and .structured_output == null'
}

@test "codex result: tool failures and metadata warnings can recover within a successful turn" {
    _codex_fixture
    CODEX_MUTATION='events.insert(1, {"type":"item.completed", "item":{"type":"error", "message":"metadata warning"}}); events.insert(3, {"type":"item.completed", "item":{"type":"command_execution", "exit_code":1, "status":"failed"}})'
    run _codex_result
    echo "$output" | jq -e '.status == "success"'
}

@test "codex result: timeout, cancellation and nonzero exit override completed output" {
    _codex_fixture
    CODEX_EXIT=124
    run _codex_result
    echo "$output" | jq -e '.status == "timed_out"'
    CODEX_EXIT=143
    run _codex_result
    echo "$output" | jq -e '.status == "cancelled"'
    CODEX_EXIT=1
    printf '429 rate limit' > "$TEST_TEMP_DIR/stderr"
    run _codex_result
    echo "$output" | jq -e '.status == "failed" and .error.kind == "rate_limit"'
}

@test "codex result: decoded secrets are scrubbed and redaction cannot disguise inconsistent output" {
    _codex_fixture
    export WORKER_TEST_SECRET=$'secret"with\\escapes\nand-newline'
    CODEX_TEXT="$WORKER_TEST_SECRET"
    printf '%s' "$CODEX_TEXT" > "$TEST_TEMP_DIR/final"
    run _codex_result
    echo "$output" | jq -e '.status == "success" and .result_text == "[REDACTED:WORKER_TEST_SECRET]"'
    printf '[REDACTED:WORKER_TEST_SECRET]' > "$TEST_TEMP_DIR/final"
    run _codex_result
    echo "$output" | jq -e '.status == "failed" and .error.kind == "transport"'
}

@test "codex result: missing usage stays unknown and absent final messages fail" {
    _codex_fixture
    CODEX_MUTATION='events[-1].pop("usage")'
    run _codex_result
    echo "$output" | jq -e '.status == "success" and .usage.input_tokens == null'
    CODEX_MUTATION='events.pop(2)'
    run _codex_result
    echo "$output" | jq -e '.status == "failed" and .error.kind == "transport"'
}

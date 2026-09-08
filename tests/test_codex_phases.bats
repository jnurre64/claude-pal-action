#!/usr/bin/env bats
load 'helpers/test_helper'
load 'helpers/codex_worker'

_phase_fixture() {
    _codex_worker
    source "$LIB_DIR/defaults.sh"
    source "$LIB_DIR/common.sh"
    engine_claude_preflight() { echo claude >> "$TEST_TEMP_DIR/preflight"; }
    engine_claude() {
        printf '%s\n' "$2" > "$TEST_TEMP_DIR/claude-tools"
        printf '%s\n' "$3" > "$TEST_TEMP_DIR/claude-model"
        printf '%s\n' "$1" > "$TEST_TEMP_DIR/claude-prompt"
        printf '%s\n' '{"result":"claude result","structured_output":{"action":"approved","verified_fixed":[],"reopened":[],"findings":[]}}'
    }
    # Keep actual Claude defaults. Explicit native selection scopes them to Claude.
    unset AGENT_CODEX_USE_NATIVE_POLICY
}

@test "codex phases: phase roles preserve advisory review versus PR revision" {
    _phase_fixture
    for phase in TRIAGE REPLY VALIDATE ADVERSARIAL_PLAN POST_IMPL_REVIEW; do
        run engine_codex_policy "$phase"
        assert_success
        echo "$output" | jq -e '.sandbox == "read-only"'
    done
    for phase in IMPLEMENT REVIEW POST_IMPL_RETRY TEST_FIX CLEANUP; do
        run engine_codex_policy "$phase"
        assert_success
        echo "$output" | jq -e '.sandbox == "workspace-write"'
    done
}

@test "codex phases: Claude implementation and Codex review route via frozen phase map" {
    _phase_fixture
    AGENT_MODEL_CLAUDE=sonnet AGENT_ENGINE_POST_IMPL_REVIEW=codex AGENT_MODEL_CODEX=gpt-custom
    AGENT_ALLOWED_TOOLS_IMPLEMENT='Read,Edit,Write,Bash(git:*)'
    AGENT_EFFORT_POST_IMPL_REVIEW=high
    agent_preflight_dispatch implement
    jq -e '.IMPLEMENT.engine == "claude" and .POST_IMPL_REVIEW.policy.sandbox == "read-only"' <<< "$AGENT_PHASE_MAP"
    run run_agent implement '' '' '' IMPLEMENT
    echo "$output" | jq -e '.engine == "claude" and .status == "success"'
    [ "$(cat "$TEST_TEMP_DIR/claude-model")" = sonnet ]
    [ "$(cat "$TEST_TEMP_DIR/claude-tools")" = "$AGENT_ALLOWED_TOOLS_IMPLEMENT" ]
    run eval 'AGENT_CODEX_USE_NATIVE_POLICY=false'
    assert_failure
    run run_agent review '' incorrect-model '' POST_IMPL_REVIEW
    echo "$output" | jq -e '.engine == "codex" and .status == "success"'
    jq -e '.argv | index("--model=gpt-custom") != null and index("read-only") != null' "$TEST_TEMP_DIR/invocation.json"
    run eval 'AGENT_EFFORT_POST_IMPL_REVIEW=low'
    assert_failure
}

@test "codex phases: Codex implementation and Claude advisory review preserve model ownership" {
    _phase_fixture
    AGENT_ENGINE=codex AGENT_MODEL=gpt-custom AGENT_MODEL_CLAUDE=sonnet
    AGENT_ENGINE_POST_IMPL_REVIEW=claude
    agent_preflight_dispatch implement
    run run_agent implement '' '' '' IMPLEMENT
    echo "$output" | jq -e '.engine == "codex" and .status == "success"'
    jq -e '.argv | index("workspace-write") != null and index("--model=gpt-custom") != null' "$TEST_TEMP_DIR/invocation.json"
    run run_agent review '' '' '' POST_IMPL_REVIEW
    echo "$output" | jq -e '.engine == "claude" and .status == "success"'
    [ "$(cat "$TEST_TEMP_DIR/claude-model")" = sonnet ]
}

@test "codex phases: memory is supplied as context without an extra write grant or author session" {
    _phase_fixture
    AGENT_ENGINE=codex
    mkdir -p "$TEST_TEMP_DIR/memory"
    printf 'Shared architectural decision' > "$TEST_TEMP_DIR/memory/MEMORY.md"
    AGENT_MEMORY_DIR="$TEST_TEMP_DIR/memory"
    export AGENT_ISSUE_BODY='test task body' AGENT_FAKE_TOKEN='do-not-copy-credential'
    run run_agent review '' '' '' POST_IMPL_REVIEW
    echo "$output" | jq -e '.status == "success"'
    jq -e '.prompt | contains("Shared architectural decision") and contains("do not edit AGENTS.md or CLAUDE.md")' "$TEST_TEMP_DIR/invocation.json"
    jq -e '.prompt | contains("test task body") and (contains("do-not-copy-credential") | not)' "$TEST_TEMP_DIR/invocation.json"
    jq -e '.argv | index("--add-dir") == null and index("resume") == null' "$TEST_TEMP_DIR/invocation.json"
}

@test "codex phases: triage returns a plan that the harness materializes under read-only mode" {
    _phase_fixture
    AGENT_ENGINE=codex
    agent_preflight_dispatch new_issue
    run run_agent triage '' '' '' TRIAGE
    assert_success
    echo "$output" | jq -e '.status == "success" and .structured_output.action == "plan_ready" and (.structured_output | has("plan_markdown") | not)'
    [ "$(cat "$WORKTREE_DIR/.agent-data/plan.md")" = $'## Implementation Plan\n\nTested plan.' ]
    jq -e '.argv | index("read-only") != null and index("--add-dir") == null' "$TEST_TEMP_DIR/invocation.json"
}

@test "codex phases: missing plans and symlinked artifact directories cannot publish a stale plan" {
    _phase_fixture
    AGENT_ENGINE=codex
    mkdir -p "$WORKTREE_DIR/.agent-data"
    echo stale > "$WORKTREE_DIR/.agent-data/plan.md"
    export MOCK_TRIAGE_OUTPUT='{"action":"plan_ready"}'
    run run_agent triage '' '' '' TRIAGE
    echo "$output" | jq -e '.status == "failed" and .structured_output == null'
    [ "$(cat "$WORKTREE_DIR/.agent-data/plan.md")" = stale ]
    rm -r "$WORKTREE_DIR/.agent-data"
    mkdir "$TEST_TEMP_DIR/external"
    ln -s "$TEST_TEMP_DIR/external" "$WORKTREE_DIR/.agent-data"
    unset MOCK_TRIAGE_OUTPUT
    run run_agent triage '' '' '' TRIAGE
    echo "$output" | jq -e '.status == "failed"'
    [ ! -f "$TEST_TEMP_DIR/external/plan.md" ]
}

@test "codex phases: unsupported controls and later runtime tool additions fail without fallback" {
    _phase_fixture
    AGENT_ENGINE=codex
    AGENT_BUDGET_USD_POST_IMPL_RETRY=1
    run agent_preflight_dispatch implement
    assert_failure
    assert_output --partial 'POST_IMPL_RETRY: Codex cannot enforce the requested dollar budget'
    [ ! -f "$TEST_TEMP_DIR/invocation.json" ]
    unset AGENT_BUDGET_USD_POST_IMPL_RETRY
    AGENT_CODEX_USE_NATIVE_POLICY=false
    AGENT_ALLOWED_TOOLS_IMPLEMENT='' AGENT_ALLOWED_TOOLS_TRIAGE='' AGENT_DISALLOWED_TOOLS='' AGENT_MAX_TURNS_EXPLICIT=''
    run run_agent prompt 'Bash(custom:*)' '' '' IMPLEMENT
    echo "$output" | jq -e '.engine == "codex" and .error.kind == "configuration"'
    [ ! -f "$TEST_TEMP_DIR/invocation.json" ]
    AGENT_DISALLOWED_TOOLS='mcp__github__*'
    run engine_codex_policy POST_IMPL_REVIEW
    assert_failure
    assert_output --partial 'tool allow/deny lists'
}

@test "codex phases: terminal failure uses the existing recovery classifier" {
    _phase_fixture
    AGENT_ENGINE=codex MOCK_CODEX_MODE=failed
    run run_agent prompt '' '' '' IMPLEMENT
    echo "$output" | jq -e '.engine == "codex" and .status == "failed"'
    run classify_agent_result "$output"
    assert_output fail_fast
    [ ! -f "$TEST_TEMP_DIR/claude-model" ]
}

@test "codex phases: production engine selection invokes Codex without a test gate override" {
    _phase_fixture
    AGENT_ENGINE=codex
    run run_agent prompt '' '' '' POST_IMPL_REVIEW
    echo "$output" | jq -e '.engine == "codex" and .status == "success"'
    [ -f "$TEST_TEMP_DIR/invocation.json" ]
}

@test "codex phases: real post-implementation gate accepts structured review and rejects worker failure" {
    _phase_fixture
    source "$LIB_DIR/review-gates.sh"
    AGENT_ENGINE_POST_IMPL_REVIEW=codex
    LEDGER_FILE="$TEST_TEMP_DIR/ledger.json"
    echo '{"cycles":0,"findings":[]}' > "$LEDGER_FILE"
    set_heartbeat() { :; }
    preserve_branch() { echo preserved > "$TEST_TEMP_DIR/preserved"; }
    set_label() { echo "$1" > "$TEST_TEMP_DIR/label"; }
    gh() { echo mocked >> "$TEST_TEMP_DIR/gh-calls"; }
    run_post_impl_review
    jq -e '.action == "approved" and .findings == []' <<< "$POST_IMPL_REVIEW_JSON"
    MOCK_CODEX_MODE=failed
    run run_post_impl_review
    assert_failure
    [ "$(cat "$TEST_TEMP_DIR/label")" = agent:failed ]
    [ -f "$TEST_TEMP_DIR/preserved" ]
}

@test "codex phases: question-only triage does not create a plan artifact" {
    _phase_fixture
    AGENT_ENGINE=codex
    export MOCK_TRIAGE_OUTPUT='{"action":"ask_questions","questions":["Which behavior?"]}'
    run run_agent triage '' '' '' TRIAGE
    echo "$output" | jq -e '.status == "success" and .structured_output.action == "ask_questions"'
    [ ! -e "$WORKTREE_DIR/.agent-data/plan.md" ]
}

@test "codex phases: unsupported triage schema is rejected before any worker" {
    _phase_fixture
    AGENT_ENGINE=codex AGENT_JSON_SCHEMA_TRIAGE="$TEST_TEMP_DIR/schema.json"
    echo '{"allOf":[{"type":"object"}]}' > "$AGENT_JSON_SCHEMA_TRIAGE"
    run agent_preflight_dispatch new_issue
    assert_failure
    assert_output --partial 'TRIAGE: unsupported Codex phase schema'
    [ ! -f "$TEST_TEMP_DIR/invocation.json" ]
}

@test "codex phases: explicit Claude turn caps and permission modes are not silently ignored" {
    _phase_fixture
    AGENT_CODEX_USE_NATIVE_POLICY=false
    AGENT_ALLOWED_TOOLS_IMPLEMENT='' AGENT_DISALLOWED_TOOLS=''
    AGENT_MAX_TURNS_EXPLICIT=x
    run engine_codex_policy IMPLEMENT
    assert_failure
    assert_output --partial 'Claude-only cap'
    AGENT_MAX_TURNS_EXPLICIT=''
    AGENT_PERMISSION_MODE_IMPLEMENT=acceptEdits
    run engine_codex_policy IMPLEMENT
    assert_failure
    assert_output --partial 'Claude permission modes'
}

@test "codex phases: native selection scopes configured Claude controls including runtime label tools" {
    _phase_fixture
    AGENT_ENGINE=codex
    AGENT_MCP_CONFIG='/private/claude-only.json' AGENT_STRICT_MCP=true
    AGENT_MAX_TURNS=7 AGENT_MAX_TURNS_EXPLICIT=x
    AGENT_EXTRA_TOOLS='Bash(npm:*)' LABEL_EXTRA_TOOLS='Bash(custom:*)'
    agent_preflight_dispatch implement
    run run_agent prompt "$(get_implementation_tools)" '' '' IMPLEMENT
    echo "$output" | jq -e '.engine == "codex" and .status == "success"'
    jq -e '.argv | index("--strict-mcp-config") == null and index("--max-turns") == null and index("--allowedTools") == null and index("--ignore-user-config") == null and index("--ignore-rules") == null' "$TEST_TEMP_DIR/invocation.json"
    ! grep -q '/private/claude-only.json' "$TEST_TEMP_DIR/invocation.json"
}

@test "codex phases: native selection rejects phase-specific restrictions it cannot enforce" {
    _phase_fixture
    AGENT_BUDGET_USD=2
    run engine_codex_policy IMPLEMENT
    assert_failure
    assert_output --partial 'dollar budget'
    unset AGENT_BUDGET_USD
    AGENT_PERMISSION_MODE_IMPLEMENT=dontAsk
    run engine_codex_policy IMPLEMENT
    assert_failure
    assert_output --partial 'Claude permission modes'
    unset AGENT_PERMISSION_MODE_IMPLEMENT
    AGENT_CODEX_USE_NATIVE_POLICY=typo
    run engine_codex_policy IMPLEMENT
    assert_failure
    assert_output --partial 'must be true or false'
}

@test "codex phases: explicitly requested strict compatibility names conflicting Claude controls" {
    _phase_fixture
    AGENT_CODEX_USE_NATIVE_POLICY=false
    run engine_codex_policy IMPLEMENT
    assert_failure
    assert_output --partial 'Claude tool allow/deny lists'
    AGENT_ALLOWED_TOOLS_IMPLEMENT='' AGENT_DISALLOWED_TOOLS=''
    AGENT_MAX_TURNS_EXPLICIT=''
    AGENT_MCP_CONFIG=config.json
    run engine_codex_policy IMPLEMENT
    assert_failure
    assert_output --partial 'AGENT_MCP_CONFIG'
}

@test "codex phases: Claude-only dispatch does not validate or require unused native settings" {
    _phase_fixture
    AGENT_CODEX_USE_NATIVE_POLICY=invalid-unused-setting
    agent_preflight_dispatch implement
    [ "$(cat "$TEST_TEMP_DIR/preflight")" = claude ]
    run run_agent prompt "$(get_implementation_tools)" '' '' IMPLEMENT
    echo "$output" | jq -e '.engine == "claude" and .status == "success"'
    [ "$(cat "$TEST_TEMP_DIR/claude-tools")" = "$(get_implementation_tools)" ]
    [ ! -f "$TEST_TEMP_DIR/invocation.json" ]
}

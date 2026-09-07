#!/bin/bash
AGENT_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091  # Runtime sibling path.
source "${AGENT_LIB_DIR}/engine-claude.sh"

# stdout is always one envelope, including preflight and process failures.
# Keep the existing argument order while consumers migrate to the neutral API.
run_agent() (
    set -euo pipefail
    local prompt="$1" allowed_tools="${2:-$AGENT_ALLOWED_TOOLS_IMPLEMENT}"
    local model="${3:-}" schema="${4:-}" phase="${5:-}"
    local schema_json="" error stderr_log raw exit_code=0 normalized
    if ! python3 "${AGENT_LIB_DIR}/agent-result.py" check-dependency >/dev/null 2>&1; then
        agent_failure "$phase" configuration 'Install worker dependencies: python3 -m pip install -r scripts/requirements-worker.txt'
        return
    fi
    if [ -n "$schema" ]; then
        if [[ "$schema" != /* ]] && [ -n "${CONFIG_DIR:-}" ]; then
            schema="${CONFIG_DIR}/${schema}"
        fi
        if ! schema_json=$(python3 "${AGENT_LIB_DIR}/agent-result.py" check-schema "$schema" 2>/dev/null); then
            agent_failure "$phase" configuration 'Configured schema is missing, invalid, or uses unsupported external references'
            return
        fi
    fi
    # Unique restricted capture files; never reuse a phase's previous output.
    # shellcheck disable=SC2153  # AGENT_LOG_DIR comes from dispatch configuration.
    stderr_log=$(mktemp "${AGENT_LOG_DIR}/claude-stderr-${phase:-phase}-XXXXXX.log") || {
        agent_failure "$phase" configuration 'Cannot create worker capture file'
        return
    }
    raw=$(engine_claude "$prompt" "$allowed_tools" "$model" "$schema_json" "$phase" 2>"$stderr_log") || exit_code=$?
    error=$(redact_secrets < "$stderr_log")
    printf '%s\n' "$error" > "$stderr_log"
    # The normalizer scrubs decoded fields before schema validation and JSON
    # serialization, so escaped credentials cannot evade capture redaction.
    if normalized=$(printf '%s' "$raw" | python3 "${AGENT_LIB_DIR}/agent-result.py" normalize "$phase" "$exit_code" "$schema_json" "$stderr_log" 2>/dev/null); then
        printf '%s\n' "$normalized"
    else
        agent_failure "$phase" transport 'Unable to normalize worker result'
    fi
)

agent_failure() {
    jq -cn --arg phase "$1" --arg kind "$2" --arg message "$3" '{
        version:1, engine:"claude", phase:$phase, process_exit_code:null,
        status:"failed", error:{kind:$kind,message:$message}, result_text:"",
        structured_output:null, schema_status:"not_checked", permission_denials:[],
        denials_available:false, usage:{input_tokens:null,output_tokens:null,cached_input_tokens:null},cost_usd:null
    }'
}

agent_succeeded() {
    printf '%s' "$1" | jq -e '.version == 1 and .status == "success"' >/dev/null 2>&1
}

parse_agent_output() {
    printf '%s' "$1" | jq -r 'if .status == "success" then .result_text
        else "Agent phase failed: " + (.error.message // "unknown failure") end'
}

classify_agent_result() {
    printf '%s' "$1" | jq -r 'if .version != 1 then "fail_fast"
        elif .status == "success" then "ok"
        elif .status == "timed_out" or .error.kind == "rate_limit" or .error.kind == "limit" then "recoverable"
        else "fail_fast" end' 2>/dev/null || printf 'fail_fast\n'
}

# A failed read/decision phase must never advance based on partial JSON.
require_agent_success() {
    local result="$1" phase="$2"
    agent_succeeded "$result" && return 0
    local detail
    detail=$(parse_agent_output "$result")
    log "${phase}: ${detail}"
    set_label "agent:failed"
    gh issue comment "$NUMBER" --repo "$REPO" --body "Agent ${phase} failed: ${detail}" 2>/dev/null || true
    return 1
}

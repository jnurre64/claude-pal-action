#!/bin/bash
# ─── Run Claude and capture structured output ────────────────────
engine_claude() (
    set -euo pipefail
    local prompt="$1"
    local allowed_tools="${2:-$AGENT_ALLOWED_TOOLS_IMPLEMENT}"
    local model_override="${3:-}"
    local schema_file="${4:-}"
    local phase="${5:-}"
    local memory
    memory=$(load_shared_memory)

    cd "$WORKTREE_DIR" || return 1
    local claude_args=(
        -p "$prompt"
        --allowedTools "$allowed_tools"
        --disallowedTools "$AGENT_DISALLOWED_TOOLS"
        --max-turns "$AGENT_MAX_TURNS"
        --output-format json
    )
    local effective_model="$model_override"
    if [ -n "$effective_model" ]; then
        claude_args+=(--model "$effective_model")
    fi
    # Path gating is separate from tool rules: a command matching an
    # allow rule is still denied when it touches a path outside the
    # working directory. Sibling repos, scratch areas and package
    # caches need --add-dir (#93).
    if [ -n "${AGENT_ADD_DIRS:-}" ]; then
        local add_dir
        for add_dir in $AGENT_ADD_DIRS; do
            claude_args+=(--add-dir "$add_dir")
        done
    fi
    # The memory directory is usually out-of-tree; without --add-dir the
    # Read of a pointed-at memory file would be path-gated (#97).
    local memory_dir
    memory_dir=$(_resolve_memory_dir)
    if [ -n "$memory_dir" ]; then
        claude_args+=(--add-dir "$memory_dir")
    fi
    # Per-phase invocation flags (#98). Every one optional, defaulting to
    # current behaviour — budget in particular is LIMITLESS unless set:
    # turns and dollars are not interchangeable bounds, but a cap is the
    # operator's choice, never the harness's.
    if [ -n "$phase" ]; then
        local _var
        _var="AGENT_BUDGET_USD_${phase}"
        local budget="${!_var:-${AGENT_BUDGET_USD:-}}"
        [ -n "$budget" ] && claude_args+=(--max-budget-usd "$budget")
        _var="AGENT_EFFORT_${phase}"
        local effort="${!_var:-}"
        [ -n "$effort" ] && claude_args+=(--effort "$effort")
        _var="AGENT_PERMISSION_MODE_${phase}"
        local permission_mode="${!_var:-}"
        [ -n "$permission_mode" ] && claude_args+=(--permission-mode "$permission_mode")
    fi
    # Gate the MCP tool surface explicitly: without --strict-mcp-config a
    # phase silently inherits the operator's personal MCP servers —
    # "inherit identity, memory and skills; gate the tool surface."
    if [ -n "${AGENT_MCP_CONFIG:-}" ]; then
        claude_args+=(--mcp-config "$AGENT_MCP_CONFIG" --strict-mcp-config)
    elif [ "${AGENT_STRICT_MCP:-}" = "true" ]; then
        claude_args+=(--strict-mcp-config)
    fi
    # Headless phases should not accumulate resumable sessions
    if [ "${AGENT_SESSION_PERSISTENCE:-false}" != "true" ]; then
        claude_args+=(--no-session-persistence)
    fi
    if [ -n "$memory" ]; then
        claude_args+=(--append-system-prompt "$memory")
    fi
    # run_agent has resolved and checked this schema before invocation.
    if [ -n "$schema_file" ]; then
        claude_args+=(--json-schema "$schema_file")
    fi
    timeout "$AGENT_TIMEOUT" claude "${claude_args[@]}"
)

# Authentication status is a local check: never print identity/credential data.
# Invocations still classify revoked credentials and quota failures separately.
engine_claude_preflight() {
    command -v claude >/dev/null 2>&1 || { echo 'Claude CLI is missing' >&2; return 1; }
    command -v timeout >/dev/null 2>&1 || { echo 'timeout is missing' >&2; return 1; }
    if ! timeout 15 claude auth status --json 2>/dev/null | jq -e '.loggedIn == true' >/dev/null 2>&1; then
        echo 'Claude authentication is unavailable; configure API credentials or a saved Claude login' >&2
        return 1
    fi
}

engine_claude_check_policy() {
    local phase="$1" var value
    if [[ ! "${AGENT_TIMEOUT:-}" =~ ^[0-9]+$ ]] || [[ "${AGENT_TIMEOUT:-}" =~ ^0+$ ]]; then
        echo 'AGENT_TIMEOUT must be a positive integer number of seconds' >&2; return 1
    fi
    if [[ ! "${AGENT_MAX_TURNS:-}" =~ ^[0-9]+$ ]] || [[ "${AGENT_MAX_TURNS:-}" =~ ^0+$ ]]; then
        echo 'AGENT_MAX_TURNS must be a positive integer' >&2; return 1
    fi
    var="AGENT_BUDGET_USD_${phase}"
    value="${!var:-${AGENT_BUDGET_USD:-}}"
    if [ -n "$value" ] && { [[ ! "$value" =~ ^[0-9]+([.][0-9]+)?$ ]] || [[ "$value" =~ ^0+([.]0+)?$ ]]; }; then
        echo "${phase}: budget must be a positive dollar amount" >&2; return 1
    fi
    var="AGENT_EFFORT_${phase}"
    value="${!var:-${AGENT_EFFORT_LEVEL:-high}}"
    case "$value" in low|medium|high|xhigh|max) ;; *) echo "${phase}: unsupported Claude effort" >&2; return 1 ;; esac
    var="AGENT_PERMISSION_MODE_${phase}"
    case "${!var:-}" in ''|default|acceptEdits|auto|bypassPermissions|manual|dontAsk|plan) ;; *) echo "${phase}: unsupported Claude permission mode" >&2; return 1 ;; esac
}

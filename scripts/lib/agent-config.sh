#!/bin/bash
# Resolve only phases reachable by this event. No worker or GitHub mutations.
agent_reachable_phases() {
    local event="$1" implementation=false
    case "$event" in
        status) return ;;
        new_issue) echo TRIAGE ;;
        issue_reply)
            printf '%s\n' REPLY TRIAGE
            if [ "${AGENT_ALLOW_DIRECT_IMPLEMENT:-true}" = true ]; then
                echo VALIDATE
                implementation=true
            fi ;;
        direct_implement)
            if [ "${AGENT_ALLOW_DIRECT_IMPLEMENT:-true}" = true ]; then
                echo VALIDATE
                implementation=true
            fi ;;
        implement) implementation=true ;;
        pr_review) echo REVIEW ;;
        post_merge) [ "${AGENT_CLEANUP_ENABLED:-true}" != true ] || echo CLEANUP ;;
        *) echo 'Unknown dispatch event' >&2; return 1 ;;
    esac
    if [ "$implementation" = true ]; then
        [ "${AGENT_ADVERSARIAL_PLAN_REVIEW:-true}" != true ] || echo ADVERSARIAL_PLAN
        echo IMPLEMENT
        # Match the gates' fallback for invalid retry counts, without arithmetic
        # evaluation of operator-provided strings (or octal parsing of 08).
        if [ -n "${AGENT_TEST_COMMAND:-}" ] && [[ ! "${AGENT_TEST_GATE_MAX_RETRIES:-2}" =~ ^0+$ ]]; then
            echo TEST_FIX
        fi
        if [ "${AGENT_POST_IMPL_REVIEW:-true}" = true ]; then
            echo POST_IMPL_REVIEW
            [[ "${AGENT_POST_IMPL_REVIEW_MAX_RETRIES:-3}" =~ ^0+$ ]] || echo POST_IMPL_RETRY
        fi
    fi
}

agent_resolve_phase() {
    local phase="$1" explicit_model="${2:-}" engine model var default_engine="${AGENT_ENGINE:-claude}"
    case "$phase" in
        ''|TRIAGE|REPLY|VALIDATE|IMPLEMENT|REVIEW|ADVERSARIAL_PLAN|POST_IMPL_REVIEW|POST_IMPL_RETRY|TEST_FIX|CLEANUP) ;;
        *) echo 'Unknown worker phase' >&2; return 1 ;;
    esac
    case "$default_engine" in claude|codex) ;; *) echo 'AGENT_ENGINE must be claude or codex' >&2; return 1 ;; esac
    var="AGENT_ENGINE_${phase}"
    engine="${!var:-$default_engine}"
    case "$engine" in claude|codex) ;; *) echo "AGENT_ENGINE_${phase} must be claude or codex" >&2; return 1 ;; esac
    var="AGENT_MODEL_${phase}"
    model="${explicit_model:-${!var:-}}"
    # Historical REPLY/VALIDATE inherited TRIAGE. Preserve that only when
    # both phases use the same engine; never leak a model across engines.
    if [ -z "$model" ] && [[ "$phase" = REPLY || "$phase" = VALIDATE ]] &&
        [ "$engine" = "${AGENT_ENGINE_TRIAGE:-$default_engine}" ]; then
        model="${AGENT_MODEL_TRIAGE:-}"
    fi
    var="AGENT_MODEL_${engine^^}"
    model="${model:-${!var:-}}"
    if [ -z "$model" ] && [ "$engine" = "$default_engine" ]; then
        model="${AGENT_MODEL:-}"
    fi
    # Reject recognizable cross-provider mistakes; custom provider model IDs
    # remain opaque and are passed unchanged to their selected CLI.
    case "$engine:$model" in
        codex:claude*|codex:sonnet*|codex:opus*|codex:haiku*|claude:gpt-*|claude:o[134]|claude:o[134]-*)
            echo "Model is incompatible with the ${engine} engine for ${phase:-worker}" >&2; return 1 ;;
    esac
    jq -cn --arg engine "$engine" --arg model "$model" '{engine:$engine,model:$model}'
}

agent_check_schema() {
    local schema="$1"
    [ -n "$schema" ] || return 0
    if [[ "$schema" != /* ]] && [ -n "${CONFIG_DIR:-}" ]; then
        schema="${CONFIG_DIR}/${schema}"
    fi
    python3 "${AGENT_LIB_DIR}/agent-result.py" check-schema "$schema" 2>/dev/null
}

agent_preflight_dispatch() {
    local phases phase resolved engine schema var map='{}' checked_claude=false checked_codex=false policy
    phases=$(agent_reachable_phases "$1") || return 1
    [ -n "$phases" ] || return 0
    if ! python3 "${AGENT_LIB_DIR}/agent-result.py" check-dependency >/dev/null 2>&1; then
        echo 'Install worker dependencies: python3 -m pip install -r scripts/requirements-worker.txt' >&2
        return 1
    fi
    for phase in $phases; do
        resolved=$(agent_resolve_phase "$phase") || return 1
        engine=$(jq -r .engine <<< "$resolved")
        # Validate the selected engine; never fall back to a different engine.
        if ! agent_engine_enabled "$engine"; then
            echo "${phase}: Unsupported worker engine" >&2
            return 1
        fi
        var="AGENT_JSON_SCHEMA_${phase}"
        if ! schema=$(agent_check_schema "${!var:-}"); then
            echo "${phase}: configured schema is missing, invalid, or unsupported" >&2
            return 1
        fi
        case "$engine" in
            claude)
                engine_claude_check_policy "$phase" || return 1
                if [ "$checked_claude" = false ]; then
                    engine_claude_preflight || return 1
                    checked_claude=true
                fi ;;
            codex)
                policy=$(engine_codex_policy "$phase") || return 1
                if ! printf '%s' "$schema" | python3 "${AGENT_LIB_DIR}/codex-worker.py" check-phase-schema "$phase"; then
                    echo "${phase}: unsupported Codex phase schema" >&2; return 1
                fi
                if [ "$checked_codex" = false ]; then
                    engine_codex_preflight || return 1
                    checked_codex=true
                fi
                if [ "$(jq -r .use_native_policy <<< "$policy")" = true ]; then
                    log "${phase}: Codex native policy selected; Claude tool lists (including label tools), MCP configuration and turn caps apply only to Claude. Codex uses native integrations and AGENT_TIMEOUT; no turn or dollar cap is claimed."
                fi
                resolved=$(jq --argjson policy "$policy" '. + {policy:$policy}' <<< "$resolved") ;;
        esac
        resolved=$(jq --arg schema "$schema" '. + {schema_json:$schema}' <<< "$resolved")
        map=$(jq -c --arg phase "$phase" --argjson config "$resolved" '. + {($phase):$config}' <<< "$map")
    done
    # Readonly shell state prevents later harness code from changing policy.
    # It is not a sandbox boundary against workers or file content changes.
    AGENT_PHASE_MAP="$map"
    # shellcheck disable=SC2034  # Consumed by run_agent in agent.sh.
    readonly AGENT_PHASE_MAP
    local name
    for name in AGENT_CODEX_USE_NATIVE_POLICY AGENT_TIMEOUT AGENT_MAX_TURNS AGENT_MAX_TURNS_EXPLICIT AGENT_BUDGET_USD AGENT_EFFORT_LEVEL \
        AGENT_MCP_CONFIG AGENT_STRICT_MCP AGENT_SESSION_PERSISTENCE AGENT_ADD_DIRS \
        AGENT_MEMORY_FILE AGENT_MEMORY_DIR AGENT_DISALLOWED_TOOLS AGENT_EXTRA_TOOLS \
        AGENT_ADVERSARIAL_PLAN_REVIEW AGENT_POST_IMPL_REVIEW AGENT_POST_IMPL_REVIEW_MAX_RETRIES \
        AGENT_TEST_COMMAND AGENT_TEST_SETUP_COMMAND AGENT_TEST_GATE_MAX_RETRIES \
        AGENT_ALLOW_DIRECT_IMPLEMENT AGENT_CLEANUP_ENABLED; do
        readonly "$name"
    done
    for phase in $phases; do
        for name in AGENT_BUDGET_USD AGENT_EFFORT AGENT_PERMISSION_MODE; do
            readonly "${name}_${phase}"
        done
    done
    while IFS= read -r name; do
        case "$name" in
            AGENT_ENGINE*|AGENT_MODEL*|AGENT_ALLOWED_TOOLS_*|AGENT_LABEL_TOOLS_*|AGENT_BUDGET_USD_*|AGENT_EFFORT_*|AGENT_PERMISSION_MODE_*|AGENT_JSON_SCHEMA_*)
                readonly "$name" ;;
        esac
    done < <(compgen -A variable AGENT_)
    for phase in $phases; do
        log "Worker ${phase}: $(jq -r --arg phase "$phase" '.[$phase] | .engine + " model=" + (if .model == "" then "CLI default" else .model end)' <<< "$map")"
    done
}

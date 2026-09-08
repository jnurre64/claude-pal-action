#!/bin/bash
# shellcheck disable=SC1091,SC2034 # Globals are consumed by dispatcher and helper.
# Library: preserve the caller's shell options; entry points enable strict mode.

# Shared dispatcher/helper loading; only the new selector guarantees env priority.
agent_load_project_config() {
    CONFIG_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
    AGENT_PROFILE_INCOMING="${AGENT_PROFILE:-}"
    # Source committed defaults first (standalone mode: .sandbox-pal-dispatch/config.defaults.env)
    AGENT_DEFAULTS="${SCRIPT_DIR}/../config.defaults.env"
    if [ -f "$AGENT_DEFAULTS" ]; then
        # shellcheck source=/dev/null
        source "$AGENT_DEFAULTS"
        CONFIG_DIR="$(cd "$(dirname "$AGENT_DEFAULTS")" && pwd)"
        export CONFIG_DIR
    fi

    # Source optional overrides (may contain secrets — never commit this file)
    AGENT_CONFIG="${AGENT_CONFIG:-}"
    if [ -n "$AGENT_CONFIG" ] && [ -f "$AGENT_CONFIG" ]; then
        # shellcheck source=/dev/null
        source "$AGENT_CONFIG"
        CONFIG_DIR="$(cd "$(dirname "$AGENT_CONFIG")" && pwd)"
        export CONFIG_DIR
    elif [ -f "${SCRIPT_DIR}/../config.env" ]; then
        # shellcheck source=/dev/null
        source "${SCRIPT_DIR}/../config.env"
        CONFIG_DIR="$(cd "$(dirname "${SCRIPT_DIR}/../config.env")" && pwd)"
        export CONFIG_DIR
    fi

    # Preview needs no bot identity; dispatch retains the required assertion.
    if [ "${1:-}" = preview ]; then AGENT_BOT_USER="${AGENT_BOT_USER:-profile-preview}"; fi

    # Source defaults (fills in anything not set by either config file)
    # shellcheck source=lib/defaults.sh
    source "${SCRIPT_DIR}/lib/defaults.sh"

    CONFIG_DIR="${CONFIG_DIR:-$(cd "$SCRIPT_DIR/.." && pwd)}"
    export CONFIG_DIR
}

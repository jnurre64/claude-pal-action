#!/bin/bash
# shellcheck disable=SC1091,SC2034 # Globals are consumed by sourced modules.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/config-load.sh"
source "$SCRIPT_DIR/lib/agent.sh"

usage() {
    echo 'Usage: agent-profile.sh list | show [NAME] [--json] | use NAME | capture NAME'
    echo 'Uses dispatch AGENT_CONFIG and CONFIG_DIR. Preview performs no auth or worker calls.'
}
case "${1:-}" in -h|--help) usage; exit 0 ;; esac
agent_load_project_config preview
agent_profiles_load
command="${1:-}"; name="${2:-}"
case "$command" in
    list)
        [ "$#" -eq 1 ] || { usage >&2; exit 1; }
        printf '%s\n' legacy
        jq -r '.profiles | keys[]' <<< "$AGENT_PROFILE_CATALOG"
        ;;
    show|use)
        format=text
        if [ "$name" = --json ]; then format=json; name=''; fi
        if [ "${3:-}" = --json ]; then format=json; elif [ "$#" -gt 2 ]; then usage >&2; exit 1; fi
        [ "$#" -le 3 ] || { usage >&2; exit 1; }
        if [ "$command" = use ] && { [ -z "$name" ] || [ "$format" != text ]; }; then usage >&2; exit 1; fi
        if [ -n "$name" ]; then AGENT_PROFILE_SOURCE="command"; fi
        agent_profile_select "${name:-$AGENT_SELECTED_PROFILE}"
        preview=$(agent_profile_preview)
        if [ "$command" = use ]; then
            agent_profile_atomic_write "$AGENT_PROFILE_STATE_PATH" "$AGENT_SELECTED_PROFILE"
            echo 'Saved selection; incoming AGENT_PROFILE overrides this for individual runs.'
        fi
        if [ "$format" = json ]; then printf '%s\n' "$preview"; else agent_profile_print <<< "$preview"; fi
        ;;
    capture)
        if [ "$#" -ne 2 ] || ! agent_profile_name_valid "$name" || [ "$name" = legacy ]; then usage >&2; exit 1; fi
        # Serialize read/modify/write to prevent two captures from losing data.
        lock="${AGENT_PROFILES_PATH}.lock"
        if ! mkdir "$lock"; then echo 'Catalog is being edited; retry capture after the other writer finishes' >&2; exit 1; fi
        trap 'rmdir "$lock"' EXIT
        AGENT_PROFILES_LOADED=false
        agent_profiles_load
        if jq -e --arg name "$name" '.profiles | has($name)' <<< "$AGENT_PROFILE_CATALOG" >/dev/null; then
            echo 'Profile already exists; capture refuses to overwrite it' >&2; exit 1
        fi
        AGENT_SELECTED_PROFILE=legacy
        AGENT_NAMED_PROFILE='{}'
        routes='{}'
        for phase in $(agent_phases); do
            engine=$(agent_route_engine "$phase")
            routes=$(jq -c --arg phase "$phase" --arg engine "$engine" '. + {($phase):$engine}' <<< "$routes")
        done
        catalog=$(jq -c --arg name "$name" --arg engine "${AGENT_ENGINE:-claude}" --argjson phases "$routes" \
            '.profiles[$name] = {engine:$engine,phases:$phases,settings:{}}' <<< "$AGENT_PROFILE_CATALOG")
        agent_catalog_validate <<< "$catalog" || { echo 'Legacy routing contains an invalid engine' >&2; exit 1; }
        agent_profile_atomic_write "$AGENT_PROFILES_PATH" "$catalog"
        echo "Captured $name; active selection unchanged. Engine settings remain shared."
        ;;
    *) usage >&2; exit 1 ;;
esac

#!/bin/bash
# Library: preserve the caller's shell options; entry points enable strict mode.

agent_phases() {
    printf '%s\n' TRIAGE REPLY VALIDATE IMPLEMENT REVIEW ADVERSARIAL_PLAN POST_IMPL_REVIEW POST_IMPL_RETRY TEST_FIX CLEANUP
}

agent_phase_valid() {
    local phase
    [ -n "$1" ] || return 0
    for phase in $(agent_phases); do
        [ "$phase" != "$1" ] || return 0
    done
    return 1
}

agent_profile_name_valid() {
    [[ "$1" =~ ^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$ ]]
}

agent_catalog_validate() {
    local keys engine setting phase
    keys=$(
        for engine in claude codex; do
            while read -r setting; do
                for phase in '' $(agent_phases); do
                    printf '%s\n' "AGENT_${setting}_${engine^^}${phase:+_$phase}"
                done
            done < <(agent_setting_registry "$engine")
        done | jq -Rsc 'split("\n")[:-1]'
    )
    jq -se --argjson keys "$keys" --argjson phases "$(agent_phases | jq -Rsc 'split("\n")[:-1]')" '
        def name: type == "string" and test("^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$");
        def engine: . == "claude" or . == "codex";
        length == 1 and (.[0] | type == "object" and (keys - ["version","default","profiles"] == []) and
        .version == 1 and (.profiles | type == "object") and
        (all(.profiles | to_entries[];
            (.key | name and . != "legacy") and
            (.value | type == "object" and (keys - ["engine","phases","settings"] == []) and
                (.engine | engine) and
                ((if has("phases") then .phases else {} end) |
                    type == "object" and all(to_entries[]; (.key as $k | $phases | index($k)) != null and (.value | engine))) and
                ((if has("settings") then .settings else {} end) |
                    type == "object" and all(to_entries[]; (.key as $k | $keys | index($k)) != null and (.value | type == "string" and (contains("\u0000") | not))))))) and
        (if has("default") then (.default | name) and (.default == "legacy" or .profiles[.default] != null) else true end))
    ' >/dev/null 2>&1
}

# Data is read once, never sourced. Absent optional catalogs preserve legacy mode.
agent_profiles_load() {
    [ "${AGENT_PROFILES_LOADED:-false}" != true ] || return 0
    local root="${CONFIG_DIR:-${AGENT_LIB_DIR}/../..}" state='' requested="${AGENT_PROFILES_FILE:-}"
    AGENT_PROFILES_PATH="${AGENT_PROFILES_FILE:-agent-profiles.json}"
    AGENT_PROFILE_STATE_PATH="${AGENT_PROFILE_STATE_FILE:-.agent-profile}"
    [[ "$AGENT_PROFILES_PATH" = /* ]] || AGENT_PROFILES_PATH="$root/$AGENT_PROFILES_PATH"
    [[ "$AGENT_PROFILE_STATE_PATH" = /* ]] || AGENT_PROFILE_STATE_PATH="$root/$AGENT_PROFILE_STATE_PATH"
    AGENT_PROFILE_CATALOG='{"version":1,"profiles":{}}'
    if [ -e "$AGENT_PROFILES_PATH" ]; then
        AGENT_PROFILE_CATALOG=$(cat "$AGENT_PROFILES_PATH") || return 1
        if ! agent_catalog_validate <<< "$AGENT_PROFILE_CATALOG"; then
            echo 'Invalid agent profile catalog: check version, names, engines, phases and allowlisted string settings' >&2
            return 1
        fi
    elif [ -n "$requested" ]; then
        echo 'Explicit AGENT_PROFILES_FILE does not exist' >&2; return 1
    fi
    if [ -e "$AGENT_PROFILE_STATE_PATH" ]; then
        if ! jq -Rse 'test("^([a-zA-Z0-9][a-zA-Z0-9_-]{0,63})?\n*$") and (contains("\u0000") | not)' "$AGENT_PROFILE_STATE_PATH" >/dev/null 2>&1; then
            echo 'Invalid saved agent profile selector' >&2; return 1
        fi
        state=$(cat "$AGENT_PROFILE_STATE_PATH") || return 1
    fi
    AGENT_SELECTED_PROFILE="${AGENT_PROFILE_INCOMING-${AGENT_PROFILE:-}}"
    AGENT_PROFILE_SOURCE=incoming
    if [ -z "$AGENT_SELECTED_PROFILE" ]; then AGENT_SELECTED_PROFILE="$state"; AGENT_PROFILE_SOURCE=state; fi
    if [ -z "$AGENT_SELECTED_PROFILE" ]; then AGENT_SELECTED_PROFILE="${AGENT_PROFILE:-}"; AGENT_PROFILE_SOURCE=config; fi
    if [ -z "$AGENT_SELECTED_PROFILE" ]; then AGENT_SELECTED_PROFILE=$(jq -r '.default // "legacy"' <<< "$AGENT_PROFILE_CATALOG"); AGENT_PROFILE_SOURCE=catalog; fi
    AGENT_PROFILES_LOADED=true
}

agent_profile_select() {
    local name="$1"
    if ! agent_profile_name_valid "$name"; then echo 'Invalid agent profile name' >&2; return 1; fi
    if [ "$name" != legacy ]; then
        if [ "${AGENT_ENGINE_PROFILES:-false}" != true ]; then
            echo 'Named profiles require AGENT_ENGINE_PROFILES=true; first migrate unqualified Codex settings to engine-qualified keys (docs/configuration.md)' >&2
            return 1
        fi
        if ! jq -e --arg name "$name" '.profiles | has($name)' <<< "$AGENT_PROFILE_CATALOG" >/dev/null; then
            echo 'Unknown agent profile; inspect agent-profile.sh list or capture your legacy routes' >&2; return 1
        fi
    fi
    AGENT_SELECTED_PROFILE="$name"
    AGENT_PROFILE_READY=true
    AGENT_NAMED_PROFILE=$(jq -c --arg name "$name" '.profiles[$name] // {}' <<< "$AGENT_PROFILE_CATALOG")
}

agent_profiles_prepare() {
    [ "${AGENT_PROFILE_READY:-false}" != true ] || return 0
    agent_profiles_load && agent_profile_select "$AGENT_SELECTED_PROFILE"
}

agent_route_engine() {
    local phase="$1" var="AGENT_ENGINE_$1"
    if [ "${AGENT_SELECTED_PROFILE:-legacy}" != legacy ]; then
        jq -r --arg phase "$phase" '.phases[$phase] // .engine' <<< "$AGENT_NAMED_PROFILE"
    else
        printf '%s\n' "${!var:-${AGENT_ENGINE:-claude}}"
    fi
}

agent_profile_preview() {
    local phase record map='{}'
    for phase in $(agent_phases); do
        record=$(agent_resolve_config "$phase") || return 1
        map=$(jq -c --arg phase "$phase" --argjson record "$record" '. + {($phase):$record}' <<< "$map")
    done
    jq -cn --arg profile "$AGENT_SELECTED_PROFILE" --arg source "$AGENT_PROFILE_SOURCE" --argjson phases "$map" \
        '{profile:$profile,selection_source:$source,routing:(if $profile == "legacy" then "legacy routing" else "profile owns all phases; raw engine overrides inactive" end),phases:$phases}'
}

agent_profile_print() {
    jq -r '.profile + " (selection: " + .selection_source + ") — " + .routing,
        (.phases | to_entries[] | .key + ": " + .value.engine + " model=" +
        (if .value.model == "" then "CLI default" else .value.model end) +
        " settings=" + (.value.settings | tojson))'
}

agent_profile_atomic_write() {
    local destination="$1" content="$2" temporary
    if [ -d "$destination" ]; then echo 'Profile destination is a directory' >&2; return 1; fi
    temporary=$(mktemp "$(dirname "$destination")/.profile-XXXXXX") || return 1
    if printf '%s\n' "$content" > "$temporary" && mv -f "$temporary" "$destination"; then return 0; fi
    rm -f "$temporary"
    return 1
}

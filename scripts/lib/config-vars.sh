#!/bin/bash
# ─── Config variable parsing utilities ─────────────────────────────
# Provides: parse_config_vars, parse_config_vars_with_context
# Used by update.sh and setup.sh to detect and migrate new AGENT_* settings.

# parse_config_vars <file>
#   Extracts AGENT_* variable names from an env file.
#   Handles: active assignments (AGENT_FOO="bar"), commented assignments (# AGENT_FOO="bar"),
#   and bare names (# AGENT_FOO).
#   Outputs one variable name per line, sorted, deduplicated.
parse_config_vars() {
    local file="$1"
    if [ ! -f "$file" ]; then
        return 0
    fi
    grep -oP '^\s*#?\s*\KAGENT_[A-Z_]+' "$file" | sort -u
}

# parse_config_vars_with_context <file>
#   Like parse_config_vars, but for each var also extracts:
#   - The comment block above it (description)
#   - The default value
#   Outputs: VAR_NAME|default_value|comment text
parse_config_vars_with_context() {
    local file="$1"
    if [ ! -f "$file" ]; then
        return 0
    fi

    local comment_block=""
    local prev_was_comment=false

    while IFS= read -r line; do
        # Blank line resets comment accumulator
        if [[ -z "${line// /}" ]]; then
            # Only reset if the next line isn't a comment continuation
            prev_was_comment=false
            comment_block=""
            continue
        fi

        # Pure comment line (not a commented-out assignment)
        # Note: must capture BASH_REMATCH[1] before any subsequent =~ test clears it
        if [[ "$line" =~ ^[[:space:]]*#[[:space:]]*(.*) ]]; then
            local comment_text="${BASH_REMATCH[1]}"
            # Skip if this is a commented-out AGENT_ variable (handled below)
            if [[ "$comment_text" =~ ^AGENT_[A-Z_]+ ]]; then
                :  # Fall through to commented-out assignment handler
            elif [[ "$comment_text" =~ ^──.*── ]]; then
                # Section header line — reset comment block, don't accumulate
                comment_block=""
                prev_was_comment=false
                continue
            else
                if [ "$prev_was_comment" = true ] && [ -n "$comment_block" ]; then
                    comment_block="${comment_block} ${comment_text}"
                else
                    comment_block="$comment_text"
                fi
                prev_was_comment=true
                continue
            fi
        fi

        # Active assignment: AGENT_FOO="value" or AGENT_FOO=value
        if [[ "$line" =~ ^[[:space:]]*(AGENT_[A-Z_]+)=[[:space:]]*\"?([^\"]*)\"? ]]; then
            local var_name="${BASH_REMATCH[1]}"
            local var_value="${BASH_REMATCH[2]}"
            echo "${var_name}|${var_value}|${comment_block}"
            comment_block=""
            prev_was_comment=false
            continue
        fi

        # Commented-out assignment: # AGENT_FOO="value"
        if [[ "$line" =~ ^[[:space:]]*#[[:space:]]*(AGENT_[A-Z_]+)=[[:space:]]*\"?([^\"]*)\"? ]]; then
            local var_name="${BASH_REMATCH[1]}"
            local var_value="${BASH_REMATCH[2]}"
            echo "${var_name}|${var_value}|${comment_block}"
            comment_block=""
            prev_was_comment=false
            continue
        fi

        # Bare commented name: # AGENT_FOO (no assignment)
        if [[ "$line" =~ ^[[:space:]]*#[[:space:]]*(AGENT_[A-Z_]+)[[:space:]]*$ ]]; then
            local var_name="${BASH_REMATCH[1]}"
            echo "${var_name}||${comment_block}"
            comment_block=""
            prev_was_comment=false
            continue
        fi

        # Non-matching line — reset
        comment_block=""
        prev_was_comment=false
    done < "$file"
}

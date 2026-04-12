#!/usr/bin/env bats
# Tests for scripts/lib/config-vars.sh

load 'helpers/test_helper'

setup() {
    # Call parent setup from test_helper
    TEST_TEMP_DIR="$(mktemp -d)"
    export TEST_TEMP_DIR

    # Source the module under test
    source "${LIB_DIR}/config-vars.sh"
}

teardown() {
    rm -rf "$TEST_TEMP_DIR"
}

# ═══════════════════════════════════════════════════════════════
# parse_config_vars tests
# ═══════════════════════════════════════════════════════════════

@test "parse_config_vars: extracts active assignments" {
    cat > "$TEST_TEMP_DIR/test.env" << 'EOF'
AGENT_FOO="bar"
AGENT_BAZ=qux
EOF
    run parse_config_vars "$TEST_TEMP_DIR/test.env"
    assert_success
    assert_line "AGENT_FOO"
    assert_line "AGENT_BAZ"
}

@test "parse_config_vars: extracts commented-out assignments" {
    cat > "$TEST_TEMP_DIR/test.env" << 'EOF'
# AGENT_OPTIONAL="default_value"
EOF
    run parse_config_vars "$TEST_TEMP_DIR/test.env"
    assert_success
    assert_line "AGENT_OPTIONAL"
}

@test "parse_config_vars: deduplicates output" {
    cat > "$TEST_TEMP_DIR/test.env" << 'EOF'
AGENT_FOO="first"
# AGENT_FOO="second"
EOF
    run parse_config_vars "$TEST_TEMP_DIR/test.env"
    assert_success
    # Should only appear once
    [ "$(echo "$output" | grep -c 'AGENT_FOO')" -eq 1 ]
}

@test "parse_config_vars: sorts output" {
    cat > "$TEST_TEMP_DIR/test.env" << 'EOF'
AGENT_ZEBRA="z"
AGENT_ALPHA="a"
AGENT_MIDDLE="m"
EOF
    run parse_config_vars "$TEST_TEMP_DIR/test.env"
    assert_success
    assert_line --index 0 "AGENT_ALPHA"
    assert_line --index 1 "AGENT_MIDDLE"
    assert_line --index 2 "AGENT_ZEBRA"
}

@test "parse_config_vars: ignores non-AGENT lines" {
    cat > "$TEST_TEMP_DIR/test.env" << 'EOF'
SOME_OTHER_VAR="value"
PATH="/usr/bin"
AGENT_REAL="yes"
EOF
    run parse_config_vars "$TEST_TEMP_DIR/test.env"
    assert_success
    assert_line "AGENT_REAL"
    refute_line "SOME_OTHER_VAR"
    refute_line "PATH"
}

@test "parse_config_vars: returns empty for missing file" {
    run parse_config_vars "$TEST_TEMP_DIR/nonexistent.env"
    assert_success
    assert_output ""
}

@test "parse_config_vars: handles real config.defaults.env.example" {
    run parse_config_vars "${SCRIPTS_DIR}/../config.defaults.env.example"
    assert_success
    assert_line "AGENT_BOT_USER"
    assert_line "AGENT_MAX_TURNS"
    assert_line "AGENT_TIMEOUT"
}

# ═══════════════════════════════════════════════════════════════
# parse_config_vars_with_context tests
# ═══════════════════════════════════════════════════════════════

@test "parse_config_vars_with_context: extracts var with default and comment" {
    cat > "$TEST_TEMP_DIR/test.env" << 'EOF'
# Maximum number of retries
AGENT_MAX_RETRIES=3
EOF
    run parse_config_vars_with_context "$TEST_TEMP_DIR/test.env"
    assert_success
    assert_line "AGENT_MAX_RETRIES|3|Maximum number of retries"
}

@test "parse_config_vars_with_context: handles empty default" {
    cat > "$TEST_TEMP_DIR/test.env" << 'EOF'
AGENT_FOO=""
EOF
    run parse_config_vars_with_context "$TEST_TEMP_DIR/test.env"
    assert_success
    assert_line "AGENT_FOO||"
}

@test "parse_config_vars_with_context: handles commented-out assignment" {
    cat > "$TEST_TEMP_DIR/test.env" << 'EOF'
# Enable feature X
# AGENT_FEATURE_X="true"
EOF
    run parse_config_vars_with_context "$TEST_TEMP_DIR/test.env"
    assert_success
    assert_line "AGENT_FEATURE_X|true|Enable feature X"
}

@test "parse_config_vars_with_context: multi-line comment accumulates" {
    cat > "$TEST_TEMP_DIR/test.env" << 'EOF'
# First line of description
# Second line of description
AGENT_THING="value"
EOF
    run parse_config_vars_with_context "$TEST_TEMP_DIR/test.env"
    assert_success
    assert_line "AGENT_THING|value|First line of description Second line of description"
}

@test "parse_config_vars_with_context: blank line resets comment" {
    cat > "$TEST_TEMP_DIR/test.env" << 'EOF'
# This comment belongs to FOO
AGENT_FOO="1"

# This comment belongs to BAR
AGENT_BAR="2"
EOF
    run parse_config_vars_with_context "$TEST_TEMP_DIR/test.env"
    assert_success
    assert_line "AGENT_FOO|1|This comment belongs to FOO"
    assert_line "AGENT_BAR|2|This comment belongs to BAR"
}

@test "parse_config_vars_with_context: section headers are excluded" {
    cat > "$TEST_TEMP_DIR/test.env" << 'EOF'
# ── Some Section ──────────────────────────
# Actual description
AGENT_FOO="bar"
EOF
    run parse_config_vars_with_context "$TEST_TEMP_DIR/test.env"
    assert_success
    assert_line "AGENT_FOO|bar|Actual description"
}

@test "parse_config_vars_with_context: returns empty for missing file" {
    run parse_config_vars_with_context "$TEST_TEMP_DIR/nonexistent.env"
    assert_success
    assert_output ""
}

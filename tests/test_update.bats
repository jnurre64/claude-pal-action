#!/usr/bin/env bats
# Tests for scripts/update.sh

load 'helpers/test_helper'

# ═══════════════════════════════════════════════════════════════
# Source verification tests
# ═══════════════════════════════════════════════════════════════

@test "update.sh: uses dynamic file discovery (not hardcoded list)" {
    # Both installers use the shared dynamic inventory.
    grep -q 'list_install_assets' "${SCRIPTS_DIR}/update.sh"
}

@test "update.sh: tracks labels.txt" {
    grep -q 'labels.txt' "${LIB_DIR}/install-assets.sh"
}

@test "update.sh: checks assets even when version is current" {
    grep -q 'Already up to date' "${SCRIPTS_DIR}/update.sh"
}

@test "update.sh: handles missing .upstream file" {
    grep -q '.upstream tracking file not found' "${SCRIPTS_DIR}/update.sh"
}

@test "update.sh: cleans up temp directory on exit" {
    grep -q 'trap.*rm -rf' "${SCRIPTS_DIR}/update.sh"
}

# ═══════════════════════════════════════════════════════════════
# Functional tests with mock installation
# ═══════════════════════════════════════════════════════════════

_create_mock_install() {
    local install_dir="$1"
    local version="${2:-abc123}"

    mkdir -p "$install_dir/scripts/lib" "$install_dir/prompts"

    echo "#!/bin/bash" > "$install_dir/scripts/sandbox-pal-dispatch.sh"
    echo "# common functions" > "$install_dir/scripts/lib/common.sh"
    echo "# worktree management" > "$install_dir/scripts/lib/worktree.sh"
    echo "# default triage prompt" > "$install_dir/prompts/triage.md"
    echo "agent|1D76DB|Trigger" > "$install_dir/labels.txt"

    # Write .upstream tracking file
    {
        echo "repo: https://github.com/jnurre64/sandbox-pal-action.git"
        echo "version: $version"
        echo "synced_at: \"2026-03-21T00:00:00Z\""
        echo "checksums:"
        for f in scripts/sandbox-pal-dispatch.sh scripts/lib/common.sh scripts/lib/worktree.sh prompts/triage.md labels.txt; do
            if [ -f "$install_dir/$f" ]; then
                local cs
                cs=$(sha256sum "$install_dir/$f" | cut -d' ' -f1)
                echo "  ${f}: \"sha256:${cs}\""
            fi
        done
    } > "$install_dir/.upstream"
}

@test "update.sh: fails when install directory doesn't exist" {
    run bash "${SCRIPTS_DIR}/update.sh" "/nonexistent/path"
    assert_failure
    assert_output --partial "not found"
}

@test "update.sh: fails when .upstream file is missing" {
    local install_dir="${TEST_TEMP_DIR}/install"
    mkdir -p "$install_dir"

    run bash "${SCRIPTS_DIR}/update.sh" "$install_dir"
    assert_failure
    assert_output --partial ".upstream tracking file not found"
}

@test "update.sh: detects unmodified files correctly" {
    local install_dir="${TEST_TEMP_DIR}/install"
    _create_mock_install "$install_dir"

    # Verify checksums match (file unchanged = checksum matches stored)
    local stored_cs
    stored_cs=$(grep "scripts/sandbox-pal-dispatch.sh" "$install_dir/.upstream" | sed 's/.*"sha256://' | sed 's/".*//')
    local current_cs
    current_cs=$(sha256sum "$install_dir/scripts/sandbox-pal-dispatch.sh" | cut -d' ' -f1)

    assert_equal "$stored_cs" "$current_cs"
}

@test "update.sh: detects locally modified files" {
    local install_dir="${TEST_TEMP_DIR}/install"
    _create_mock_install "$install_dir"

    # Modify a file locally
    echo "# local change" >> "$install_dir/scripts/sandbox-pal-dispatch.sh"

    # Checksum should no longer match
    local stored_cs
    stored_cs=$(grep "scripts/sandbox-pal-dispatch.sh" "$install_dir/.upstream" | sed 's/.*"sha256://' | sed 's/".*//')
    local current_cs
    current_cs=$(sha256sum "$install_dir/scripts/sandbox-pal-dispatch.sh" | cut -d' ' -f1)

    [ "$stored_cs" != "$current_cs" ]
}

# ═══════════════════════════════════════════════════════════════
# REGRESSION: Files with no stored checksum treated as modified
# ═══════════════════════════════════════════════════════════════

@test "REGRESSION: files with no stored checksum are treated as locally modified" {
    # Verify the update script treats missing checksums conservatively
    # (assumes locally modified rather than assuming unmodified)
    grep -A2 'No stored checksum' "${SCRIPTS_DIR}/update.sh" | grep -q 'local_modified=true'
}

# ═══════════════════════════════════════════════════════════════
# .upstream file format tests
# ═══════════════════════════════════════════════════════════════

@test ".upstream: contains repo URL" {
    local install_dir="${TEST_TEMP_DIR}/install"
    _create_mock_install "$install_dir"

    grep -q "^repo:" "$install_dir/.upstream"
}

@test ".upstream: contains version hash" {
    local install_dir="${TEST_TEMP_DIR}/install"
    _create_mock_install "$install_dir"

    grep -q "^version:" "$install_dir/.upstream"
}

@test ".upstream: contains checksums section" {
    local install_dir="${TEST_TEMP_DIR}/install"
    _create_mock_install "$install_dir"

    grep -q "^checksums:" "$install_dir/.upstream"
}

@test ".upstream: checksums use sha256 format" {
    local install_dir="${TEST_TEMP_DIR}/install"
    _create_mock_install "$install_dir"

    grep -q '"sha256:' "$install_dir/.upstream"
}

# ═══════════════════════════════════════════════════════════════
# setup.sh tracking tests
# ═══════════════════════════════════════════════════════════════

@test "setup.sh: uses dynamic file discovery for checksums" {
    grep -q 'list_install_assets' "${SCRIPTS_DIR}/setup.sh"
}

@test "setup.sh: tracks labels.txt in .upstream" {
    # Verify labels.txt checksum is written in the .upstream tracking section
    grep -q 'labels.txt' "${LIB_DIR}/install-assets.sh"
}

@test "setup.sh: writes config_vars section to .upstream" {
    grep -q 'config_vars:' "${SCRIPTS_DIR}/setup.sh"
    grep -q 'parse_config_vars' "${SCRIPTS_DIR}/setup.sh"
}

# ═══════════════════════════════════════════════════════════════
# Config variable migration tests
# ═══════════════════════════════════════════════════════════════

_create_mock_upstream() {
    local upstream_dir="$1"
    mkdir -p "$upstream_dir/scripts/lib" "$upstream_dir/prompts"

    echo "#!/bin/bash" > "$upstream_dir/scripts/sandbox-pal-dispatch.sh"
    echo "# common functions" > "$upstream_dir/scripts/lib/common.sh"

    # Copy the real config-vars.sh so it can be sourced
    cp "${LIB_DIR}/config-vars.sh" "$upstream_dir/scripts/lib/config-vars.sh"
}

_create_mock_example_file() {
    local upstream_dir="$1"
    cat > "$upstream_dir/config.defaults.env.example" << 'EOF'
# Bot account username
AGENT_BOT_USER=""

# Max turns
AGENT_MAX_TURNS=200

# Timeout
AGENT_TIMEOUT=3600
EOF
}

_create_install_with_config_vars() {
    local install_dir="$1"
    local version="${2:-abc123}"
    shift 2
    local vars=("$@")

    _create_mock_install "$install_dir" "$version"

    # Append config_vars: section
    {
        echo "config_vars:"
        for var in "${vars[@]}"; do
            echo "  - $var"
        done
    } >> "$install_dir/.upstream"
}

@test "update.sh: sources config-vars.sh from upstream" {
    grep -q 'source.*config-vars.sh' "${SCRIPTS_DIR}/update.sh"
}

@test "update.sh: writes config_vars to .upstream tracking" {
    grep -q 'config_vars:' "${SCRIPTS_DIR}/update.sh"
    grep -q 'parse_config_vars.*config.defaults.env.example' "${SCRIPTS_DIR}/update.sh"
}

@test "update.sh: detects new config variables section" {
    grep -q 'Detect new config variables' "${SCRIPTS_DIR}/update.sh"
}

@test "update.sh: first-run shows initialization message when no config_vars" {
    grep -q 'Config variable tracking initialized' "${SCRIPTS_DIR}/update.sh"
}

@test "update.sh: has secret detection heuristic" {
    grep -q 'SECRET_KEYWORDS' "${SCRIPTS_DIR}/update.sh"
    grep -q 'TOKEN\|KEY\|SECRET\|WEBHOOK\|PASSWORD\|CREDENTIAL' "${SCRIPTS_DIR}/update.sh"
}

@test "update.sh: creates config.env backup before modifications" {
    grep -q '\.bak\.' "${SCRIPTS_DIR}/update.sh"
}

@test "update.sh: writes section header with date" {
    grep -q 'Added by /update on' "${SCRIPTS_DIR}/update.sh"
}

@test "update.sh: supports add-active, commented, and skip choices" {
    grep -q '(A)dd active' "${SCRIPTS_DIR}/update.sh"
    grep -q '(c)ommented' "${SCRIPTS_DIR}/update.sh"
    grep -q '(s)kip' "${SCRIPTS_DIR}/update.sh"
}

@test "update.sh: includes config summary in completion message" {
    grep -q 'CONFIG_TOTAL' "${SCRIPTS_DIR}/update.sh"
    grep -q 'new setting(s) detected' "${SCRIPTS_DIR}/update.sh"
}

# ═══════════════════════════════════════════════════════════════
# Config var detection logic (functional tests using config-vars.sh)
# ═══════════════════════════════════════════════════════════════

@test "config migration: stored vars parsed from .upstream config_vars section" {
    source "${LIB_DIR}/config-vars.sh"

    local install_dir="${TEST_TEMP_DIR}/install"
    _create_install_with_config_vars "$install_dir" "abc123" \
        "AGENT_BOT_USER" "AGENT_MAX_TURNS" "AGENT_TIMEOUT"

    # Verify config_vars section is present and parseable
    mapfile -t stored < <(
        sed -n '/^config_vars:/,/^[^ ]/{ /^  - /s/^  - //p }' "$install_dir/.upstream"
    )
    [ "${#stored[@]}" -eq 3 ]
    [ "${stored[0]}" = "AGENT_BOT_USER" ]
    [ "${stored[1]}" = "AGENT_MAX_TURNS" ]
    [ "${stored[2]}" = "AGENT_TIMEOUT" ]
}

@test "config migration: new vars detected by comparing upstream vs stored" {
    source "${LIB_DIR}/config-vars.sh"

    local install_dir="${TEST_TEMP_DIR}/install"
    local upstream_dir="${TEST_TEMP_DIR}/upstream"

    # Stored knows about BOT_USER and MAX_TURNS
    _create_install_with_config_vars "$install_dir" "abc123" \
        "AGENT_BOT_USER" "AGENT_MAX_TURNS"

    # Upstream adds AGENT_TIMEOUT and AGENT_NEW_FEATURE
    _create_mock_upstream "$upstream_dir"
    cat > "$upstream_dir/config.defaults.env.example" << 'EOF'
AGENT_BOT_USER=""
AGENT_MAX_TURNS=200
AGENT_TIMEOUT=3600
AGENT_NEW_FEATURE="enabled"
EOF

    mapfile -t upstream_vars < <(parse_config_vars "$upstream_dir/config.defaults.env.example")
    mapfile -t stored_vars < <(
        sed -n '/^config_vars:/,/^[^ ]/{ /^  - /s/^  - //p }' "$install_dir/.upstream"
    )

    # Compute new vars
    new_vars=()
    for var in "${upstream_vars[@]}"; do
        found=false
        for stored in "${stored_vars[@]}"; do
            if [ "$var" = "$stored" ]; then found=true; break; fi
        done
        [ "$found" = false ] && new_vars+=("$var")
    done

    [ "${#new_vars[@]}" -eq 2 ]
    [[ " ${new_vars[*]} " == *" AGENT_TIMEOUT "* ]]
    [[ " ${new_vars[*]} " == *" AGENT_NEW_FEATURE "* ]]
}

@test "config migration: already-set vars in config.env are skipped" {
    source "${LIB_DIR}/config-vars.sh"

    # Create config.env with AGENT_FOO already set
    cat > "$TEST_TEMP_DIR/config.env" << 'EOF'
AGENT_FOO="custom_value"
EOF

    mapfile -t user_vars < <(parse_config_vars "$TEST_TEMP_DIR/config.env")

    # AGENT_FOO should be detected as already set
    found=false
    for uv in "${user_vars[@]}"; do
        [ "$uv" = "AGENT_FOO" ] && found=true
    done
    [ "$found" = true ]
}

@test "config migration: commented vars in config.env are detected as present" {
    source "${LIB_DIR}/config-vars.sh"

    # User has a commented-out entry — still counts as "present"
    cat > "$TEST_TEMP_DIR/config.env" << 'EOF'
# AGENT_FOO="old_default"
EOF

    mapfile -t user_vars < <(parse_config_vars "$TEST_TEMP_DIR/config.env")

    found=false
    for uv in "${user_vars[@]}"; do
        [ "$uv" = "AGENT_FOO" ] && found=true
    done
    [ "$found" = true ]
}

@test "config migration: secret keyword heuristic detects sensitive vars" {
    # Verify vars containing TOKEN/KEY/SECRET etc. would be flagged
    secret_keywords="TOKEN|KEY|SECRET|WEBHOOK|PASSWORD|CREDENTIAL"

    echo "AGENT_API_TOKEN" | grep -qE "$secret_keywords"
    echo "AGENT_SECRET_VALUE" | grep -qE "$secret_keywords"
    echo "AGENT_WEBHOOK_URL" | grep -qE "$secret_keywords"
    echo "AGENT_PASSWORD_HASH" | grep -qE "$secret_keywords"

    # Non-secret var should NOT match
    ! echo "AGENT_MAX_TURNS" | grep -qE "$secret_keywords"
    ! echo "AGENT_TIMEOUT" | grep -qE "$secret_keywords"
}

@test "config migration: idempotent when no new vars exist" {
    source "${LIB_DIR}/config-vars.sh"

    local upstream_dir="${TEST_TEMP_DIR}/upstream"
    _create_mock_upstream "$upstream_dir"
    cat > "$upstream_dir/config.defaults.env.example" << 'EOF'
AGENT_BOT_USER=""
AGENT_MAX_TURNS=200
EOF

    # Stored list matches upstream exactly
    mapfile -t upstream_vars < <(parse_config_vars "$upstream_dir/config.defaults.env.example")
    stored_vars=("AGENT_BOT_USER" "AGENT_MAX_TURNS")

    new_vars=()
    for var in "${upstream_vars[@]}"; do
        found=false
        for stored in "${stored_vars[@]}"; do
            if [ "$var" = "$stored" ]; then found=true; break; fi
        done
        [ "$found" = false ] && new_vars+=("$var")
    done

    [ "${#new_vars[@]}" -eq 0 ]
}

@test "config migration: backup file created with date suffix" {
    local config_file="$TEST_TEMP_DIR/config.env"
    echo 'AGENT_FOO="bar"' > "$config_file"

    # Simulate backup creation
    cp "$config_file" "${config_file}.bak.$(date '+%Y%m%d')"

    # Verify backup exists and matches original
    [ -f "${config_file}.bak.$(date '+%Y%m%d')" ]
    diff -q "$config_file" "${config_file}.bak.$(date '+%Y%m%d')"
}

@test "config migration: active entry format is correct" {
    local config_file="$TEST_TEMP_DIR/config.env"
    echo 'AGENT_FOO="bar"' > "$config_file"

    # Simulate adding an active entry
    echo "" >> "$config_file"
    echo "# ── Added by /update on $(date '+%Y-%m-%d') ──" >> "$config_file"
    echo 'AGENT_NEW_VAR="default_value"' >> "$config_file"

    grep -q 'AGENT_NEW_VAR="default_value"' "$config_file"
    grep -q 'Added by /update on' "$config_file"
}

@test "config migration: commented entry format is correct" {
    local config_file="$TEST_TEMP_DIR/config.env"
    echo 'AGENT_FOO="bar"' > "$config_file"

    # Simulate adding a commented entry
    echo '# AGENT_NEW_VAR="default_value"  # (upstream default)' >> "$config_file"

    grep -q '# AGENT_NEW_VAR="default_value"  # (upstream default)' "$config_file"
}

@test "config migration: commented entry does not override defaults.sh" {
    source "${LIB_DIR}/config-vars.sh"

    # A commented-out line should not set the variable
    cat > "$TEST_TEMP_DIR/config.env" << 'EOF'
# AGENT_TEST_VAR="commented_value"  # (upstream default)
EOF

    source "$TEST_TEMP_DIR/config.env"
    # AGENT_TEST_VAR should NOT be set (it's commented out)
    [ -z "${AGENT_TEST_VAR:-}" ]
}

# Real local git upstreams exercise the entire updater without network or workers.
_asset_fixture() {
    export ASSET_UPSTREAM="$TEST_TEMP_DIR/upstream repo"
    export ASSET_INSTALL="$TEST_TEMP_DIR/install dir"
    _create_mock_install "$ASSET_INSTALL"
    mkdir -p "$ASSET_UPSTREAM"
    cp -R "$ASSET_INSTALL/scripts" "$ASSET_INSTALL/prompts" "$ASSET_INSTALL/labels.txt" "$ASSET_UPSTREAM/"
    cp "$LIB_DIR/install-assets.sh" "$ASSET_UPSTREAM/scripts/lib/"
    mkdir -p "$ASSET_UPSTREAM/schemas" "$ASSET_UPSTREAM/skills/example" \
        "$ASSET_UPSTREAM/.claude/skills/setup/templates/standalone"
    echo '{"type":"object"}' > "$ASSET_UPSTREAM/schemas/triage.json"
    echo 'skill instructions' > "$ASSET_UPSTREAM/skills/example/SKILL.md"
    local skill
    for skill in sp-work sp-status sp-revise sp-post-merge; do
        mkdir -p "$ASSET_UPSTREAM/.claude/skills/$skill"
        cp "$SCRIPTS_DIR/../.claude/skills/$skill/SKILL.md" "$ASSET_UPSTREAM/.claude/skills/$skill/"
    done
    echo 'name: workflow' > "$ASSET_UPSTREAM/.claude/skills/setup/templates/standalone/sandbox-pal-triage.yml"
    sed -i "s|^repo:.*|repo: $ASSET_UPSTREAM|" "$ASSET_INSTALL/.upstream"
    git -C "$ASSET_UPSTREAM" init -q
    git -C "$ASSET_UPSTREAM" add .
    git -C "$ASSET_UPSTREAM" -c user.name=Test -c user.email=test@example.com commit -qm initial
}

_asset_commit() {
    git -C "$ASSET_UPSTREAM" add .
    git -C "$ASSET_UPSTREAM" -c user.name=Test -c user.email=test@example.com commit -qm change
}

@test "REGRESSION v1.2.0: upgrade delivers and checksums schemas skills and workflow templates" {
    _asset_fixture
    run bash "$SCRIPTS_DIR/update.sh" --yes "$ASSET_INSTALL"
    assert_success
    assert_output --partial "Workflow templates changed"
    for file in schemas/triage.json skills/example/SKILL.md .claude/skills/setup/templates/standalone/sandbox-pal-triage.yml; do
        cmp "$ASSET_UPSTREAM/$file" "$ASSET_INSTALL/$file"
        local checksum
        checksum=$(sha256sum "$ASSET_UPSTREAM/$file" | cut -d' ' -f1)
        grep -F "  $file: \"sha256:$checksum\"" "$ASSET_INSTALL/.upstream"
    done
    run bash "$SCRIPTS_DIR/update.sh" --yes "$ASSET_INSTALL"
    assert_success
    refute_output --partial "Needs review"
    refute_output --partial "New from upstream"
}

@test "REGRESSION v1.2.0: customized schemas survive successive upstream upgrades" {
    _asset_fixture
    bash "$SCRIPTS_DIR/update.sh" --yes "$ASSET_INSTALL" >/dev/null
    echo custom > "$ASSET_INSTALL/schemas/triage.json"
    for revision in second third; do
        echo "$revision" > "$ASSET_UPSTREAM/schemas/triage.json"
        _asset_commit
        run bash "$SCRIPTS_DIR/update.sh" --yes "$ASSET_INSTALL"
        assert_success
        assert_output --partial "Needs review"
        [ "$(cat "$ASSET_INSTALL/schemas/triage.json")" = custom ]
    done
}

@test "REGRESSION v1.2.0: EOF after an applied update preserves tracking and deferred assets remain installable" {
    _asset_fixture
    echo changed >> "$ASSET_UPSTREAM/scripts/lib/common.sh"
    _asset_commit
    printf 'y\n' > "$TEST_TEMP_DIR/answers"
    run bash -c 'bash "$1/update.sh" "$2" < "$3"' _ "$SCRIPTS_DIR" "$ASSET_INSTALL" "$TEST_TEMP_DIR/answers"
    assert_success
    cmp "$ASSET_UPSTREAM/scripts/lib/common.sh" "$ASSET_INSTALL/scripts/lib/common.sh"
    [ ! -f "$ASSET_INSTALL/schemas/triage.json" ]
    run bash "$SCRIPTS_DIR/update.sh" --yes "$ASSET_INSTALL"
    assert_success
    refute_output --partial "Needs review"
    [ -f "$ASSET_INSTALL/schemas/triage.json" ]
}

@test "REGRESSION v1.2.0: missing schema is repaired even at the current version" {
    _asset_fixture
    bash "$SCRIPTS_DIR/update.sh" --yes "$ASSET_INSTALL" >/dev/null
    rm "$ASSET_INSTALL/schemas/triage.json"
    run bash "$SCRIPTS_DIR/update.sh" --yes "$ASSET_INSTALL"
    assert_success
    cmp "$ASSET_UPSTREAM/schemas/triage.json" "$ASSET_INSTALL/schemas/triage.json"
}

@test "REGRESSION v1.2.0: update safely retries an interrupted asset copy" {
    _asset_fixture
    echo changed >> "$ASSET_UPSTREAM/scripts/lib/common.sh"
    _asset_commit
    mkdir -p "$TEST_TEMP_DIR/bin"
    export REAL_CP
    REAL_CP=$(command -v cp)
    cat > "$TEST_TEMP_DIR/bin/cp" <<'MOCK'
#!/bin/bash
"$REAL_CP" "$@"
kill -TERM "$PPID"
MOCK
    chmod +x "$TEST_TEMP_DIR/bin/cp"
    run env PATH="$TEST_TEMP_DIR/bin:$PATH" bash "$SCRIPTS_DIR/update.sh" --yes "$ASSET_INSTALL"
    assert_failure
    run bash "$SCRIPTS_DIR/update.sh" --yes "$ASSET_INSTALL"
    assert_success
    refute_output --partial "Needs review"
    cmp "$ASSET_UPSTREAM/scripts/lib/common.sh" "$ASSET_INSTALL/scripts/lib/common.sh"
}

@test "REGRESSION v1.2.0: standalone setup delivers every schema and renders caller workflows" {
    _asset_fixture
    cp "$SCRIPTS_DIR/setup.sh" "$ASSET_UPSTREAM/scripts/"
    cp "$LIB_DIR/config-vars.sh" "$ASSET_UPSTREAM/scripts/lib/"
    cp -R "$SCRIPTS_DIR/../schemas/." "$ASSET_UPSTREAM/schemas/"
    cp "$SCRIPTS_DIR/../config.defaults.env.example" "$ASSET_UPSTREAM/config.defaults.env.example"
    printf '#!/bin/bash\nexit 0\n' > "$ASSET_UPSTREAM/scripts/check-prereqs.sh"
    local target="$TEST_TEMP_DIR/consumer repo"
    mkdir -p "$target"
    printf '1\nowner/repo\ntest-bot\nmain\n\n\n%s\nn\nn\n' "$target" > "$TEST_TEMP_DIR/answers"
    run bash -c 'bash "$1/scripts/setup.sh" < "$2"' _ "$ASSET_UPSTREAM" "$TEST_TEMP_DIR/answers"
    assert_success
    for schema in "$ASSET_UPSTREAM/schemas/"*.json; do
        cmp "$schema" "$target/.sandbox-pal-dispatch/schemas/$(basename "$schema")"
        grep -F "schemas/$(basename "$schema"):" "$target/.sandbox-pal-dispatch/.upstream"
    done
    for client in .claude .agents; do
        for skill in sp-work sp-status sp-revise sp-post-merge; do
            [ -L "$target/$client/skills/$skill" ]
            cmp "$ASSET_UPSTREAM/.claude/skills/$skill/SKILL.md" "$target/$client/skills/$skill/SKILL.md"
            grep -F ".claude/skills/$skill/SKILL.md:" "$target/.sandbox-pal-dispatch/.upstream"
        done
    done
    grep -qx '  - AGENT_ENGINE_PROFILES' "$target/.sandbox-pal-dispatch/.upstream"
    grep -qx '  - AGENT_TIMEOUT_CODEX_TEST_FIX' "$target/.sandbox-pal-dispatch/.upstream"
    run bash -c 'source "$1"; echo "${AGENT_ENGINE_PROFILES:-false}"' _ "$target/.sandbox-pal-dispatch/config.env"
    assert_success
    assert_output false
    [ -f "$target/.github/workflows/agent-triage.yml" ]
    [ ! -L "$target/.sandbox-pal-dispatch/skills/example/SKILL.md" ]
}

@test "REGRESSION v1.2.0: copy completed before interrupted tracking is recognized as up to date" {
    _asset_fixture
    echo changed >> "$ASSET_UPSTREAM/scripts/lib/common.sh"
    _asset_commit
    # Simulate interruption after asset rename but before .upstream rename.
    cp "$ASSET_UPSTREAM/scripts/lib/common.sh" "$ASSET_INSTALL/scripts/lib/common.sh"
    run bash "$SCRIPTS_DIR/update.sh" --yes "$ASSET_INSTALL"
    assert_success
    refute_output --partial "Needs review"
}

@test "REGRESSION v1.2.0: installed updater can replace itself without truncating its running script" {
    _asset_fixture
    cp "$SCRIPTS_DIR/update.sh" "$ASSET_UPSTREAM/scripts/update.sh"
    _asset_commit
    bash "$SCRIPTS_DIR/update.sh" --yes "$ASSET_INSTALL" >/dev/null
    # Change length near the start to expose in-place script overwrite failures.
    sed -i '2i# New updater version with a different file offset' "$ASSET_UPSTREAM/scripts/update.sh"
    _asset_commit
    run bash "$ASSET_INSTALL/scripts/update.sh" --yes "$ASSET_INSTALL"
    assert_success
    assert_output --partial "Update complete"
    cmp "$ASSET_UPSTREAM/scripts/update.sh" "$ASSET_INSTALL/scripts/update.sh"
}

@test "REGRESSION v1.2.0: untracked customized schema is never silently adopted or overwritten" {
    _asset_fixture
    mkdir -p "$ASSET_INSTALL/schemas"
    echo custom > "$ASSET_INSTALL/schemas/triage.json"
    for attempt in first second; do
        run bash "$SCRIPTS_DIR/update.sh" --yes "$ASSET_INSTALL"
        assert_success
        assert_output --partial "Needs review"
        [ "$(cat "$ASSET_INSTALL/schemas/triage.json")" = custom ]
        ! grep -q '  schemas/triage.json:' "$ASSET_INSTALL/.upstream"
    done
}

@test "REGRESSION v1.2.0: EOF at new config prompt completes asset bookkeeping without changing config" {
    _asset_fixture
    cp "$LIB_DIR/config-vars.sh" "$ASSET_UPSTREAM/scripts/lib/"
    printf 'AGENT_BOT_USER="bot"\nAGENT_NEW_FEATURE="enabled"\n' > "$ASSET_UPSTREAM/config.defaults.env.example"
    printf 'config_vars:\n  - AGENT_BOT_USER\n' >> "$ASSET_INSTALL/.upstream"
    echo 'AGENT_BOT_USER="custom-bot"' > "$ASSET_INSTALL/config.env"
    _asset_commit
    printf 'y\n' > "$TEST_TEMP_DIR/answers"
    run bash -c 'bash "$1/update.sh" "$2" < "$3"' _ "$SCRIPTS_DIR" "$ASSET_INSTALL" "$TEST_TEMP_DIR/answers"
    assert_success
    assert_output --partial '1 skipped'
    [ "$(cat "$ASSET_INSTALL/config.env")" = 'AGENT_BOT_USER="custom-bot"' ]
    grep -q '  schemas/triage.json:' "$ASSET_INSTALL/.upstream"
    grep -q '^pending_assets: 0' "$ASSET_INSTALL/.upstream"
}

@test "client skills: upgrade exposes installed sources and preserves project customizations" {
    _asset_fixture
    local project="$TEST_TEMP_DIR/consumer repo"
    mkdir -p "$project/.agents/skills/sp-work" "$project/.claude/skills"
    mv "$ASSET_INSTALL" "$project/.sandbox-pal-dispatch"
    ASSET_INSTALL="$project/.sandbox-pal-dispatch"
    echo custom > "$project/.agents/skills/sp-work/SKILL.md"
    ln -s missing-custom-skill "$project/.claude/skills/sp-revise"
    echo 'project Codex instructions' > "$project/AGENTS.md"
    echo 'project Claude instructions' > "$project/CLAUDE.md"
    run bash "$SCRIPTS_DIR/update.sh" --yes "$ASSET_INSTALL"
    assert_success
    assert_output --partial 'Preserved'
    [ "$(cat "$project/.agents/skills/sp-work/SKILL.md")" = custom ]
    [ "$(readlink "$project/.claude/skills/sp-revise")" = missing-custom-skill ]
    [ "$(cat "$project/AGENTS.md")" = 'project Codex instructions' ]
    [ "$(cat "$project/CLAUDE.md")" = 'project Claude instructions' ]
    cmp "$ASSET_UPSTREAM/.claude/skills/sp-status/SKILL.md" "$project/.agents/skills/sp-status/SKILL.md"
    # Moving the whole consuming repository must not strand discovery links.
    mv "$project" "$TEST_TEMP_DIR/moved repo"
    project="$TEST_TEMP_DIR/moved repo"
    ASSET_INSTALL="$project/.sandbox-pal-dispatch"
    echo 'new status guidance' >> "$ASSET_UPSTREAM/.claude/skills/sp-status/SKILL.md"
    _asset_commit
    run bash "$SCRIPTS_DIR/update.sh" --yes "$ASSET_INSTALL"
    assert_success
    cmp "$ASSET_UPSTREAM/.claude/skills/sp-status/SKILL.md" "$project/.agents/skills/sp-status/SKILL.md"
    cmp "$project/.claude/skills/sp-status/SKILL.md" "$project/.agents/skills/sp-status/SKILL.md"
    echo custom-source > "$project/.agents/skills/sp-status/SKILL.md"
    echo 'another upstream edit' >> "$ASSET_UPSTREAM/.claude/skills/sp-status/SKILL.md"
    _asset_commit
    run bash "$SCRIPTS_DIR/update.sh" --yes "$ASSET_INSTALL"
    assert_success
    assert_output --partial 'Needs review'
    [ "$(cat "$project/.agents/skills/sp-status/SKILL.md")" = custom-source ]
}

@test "client skills: linked discovery parents are preserved without writing through them" {
    source "$LIB_DIR/install-assets.sh"
    local project="$TEST_TEMP_DIR/project" outside="$TEST_TEMP_DIR/outside"
    mkdir -p "$project/.sandbox-pal-dispatch/.claude/skills/sp-status" "$outside" "$project/.agents"
    echo skill > "$project/.sandbox-pal-dispatch/.claude/skills/sp-status/SKILL.md"
    ln -s "$outside" "$project/.claude"
    ln -s "$outside" "$project/.agents/skills"
    run link_install_client_skills "$project/.sandbox-pal-dispatch"
    assert_success
    assert_output --partial 'configure shared skill discovery manually'
    [ -z "$(ls -A "$outside")" ]
}

@test "client skills: deferred upstream skills do not create dangling discovery links" {
    _asset_fixture
    local project="$TEST_TEMP_DIR/project"
    mkdir -p "$project"
    mv "$ASSET_INSTALL" "$project/.sandbox-pal-dispatch"
    ASSET_INSTALL="$project/.sandbox-pal-dispatch"
    run bash -c 'bash "$1/update.sh" "$2" < /dev/null' _ "$SCRIPTS_DIR" "$ASSET_INSTALL"
    assert_success
    [ ! -e "$project/.agents" ]
    [ ! -e "$project/.claude" ]
    run bash "$SCRIPTS_DIR/update.sh" --yes "$ASSET_INSTALL"
    assert_success
    [ -f "$project/.agents/skills/sp-work/SKILL.md" ]
}

@test "engine migration: update discovers all phase settings without activating Codex or replacing project choices" {
    _asset_fixture
    cp "$LIB_DIR/config-vars.sh" "$ASSET_UPSTREAM/scripts/lib/"
    cp "$SCRIPTS_DIR/../config.defaults.env.example" "$ASSET_UPSTREAM/config.defaults.env.example"
    printf 'config_vars:\n  - AGENT_BOT_USER\n' >> "$ASSET_INSTALL/.upstream"
    printf 'AGENT_ENGINE=claude\nAGENT_MODEL_CLAUDE=custom-model\nAGENT_TIMEOUT_CODEX_IMPLEMENT=4321\n' > "$ASSET_INSTALL/config.env"
    _asset_commit
    run bash "$SCRIPTS_DIR/update.sh" --yes "$ASSET_INSTALL"
    assert_success
    grep -qx 'AGENT_ENGINE=claude' "$ASSET_INSTALL/config.env"
    grep -qx 'AGENT_MODEL_CLAUDE=custom-model' "$ASSET_INSTALL/config.env"
    ! grep -q '^AGENT_CODEX_USE_NATIVE_POLICY=true' "$ASSET_INSTALL/config.env"
    grep -qx 'AGENT_TIMEOUT_CODEX_IMPLEMENT=4321' "$ASSET_INSTALL/config.env"
    grep -qx '  - AGENT_ENGINE_PROFILES' "$ASSET_INSTALL/.upstream"
    run bash -c 'source "$1"; echo "${AGENT_ENGINE_PROFILES:-false}"' _ "$ASSET_INSTALL/config.env"
    assert_success
    assert_output false
    for phase in TRIAGE REPLY VALIDATE IMPLEMENT REVIEW ADVERSARIAL_PLAN POST_IMPL_REVIEW POST_IMPL_RETRY TEST_FIX CLEANUP; do
        grep -qx "  - AGENT_ENGINE_$phase" "$ASSET_INSTALL/.upstream"
        grep -qx "  - AGENT_MODEL_$phase" "$ASSET_INSTALL/.upstream"
        for engine in CLAUDE CODEX; do
            for setting in MODEL EFFORT TIMEOUT; do
                grep -qx "  - AGENT_${setting}_${engine}_$phase" "$ASSET_INSTALL/.upstream"
            done
        done
        for setting in BUDGET_USD PERMISSION_MODE MAX_TURNS; do
            grep -qx "  - AGENT_${setting}_CLAUDE_$phase" "$ASSET_INSTALL/.upstream"
        done
    done
}

@test "named profiles: unattended update delivers example and helper preserves custom catalog state and config" {
    _asset_fixture
    cp "$SCRIPTS_DIR/../agent-profiles.example.json" "$ASSET_UPSTREAM/"
    cp "$SCRIPTS_DIR/agent-profile.sh" "$ASSET_UPSTREAM/scripts/"
    cp "$LIB_DIR/named-profiles.sh" "$LIB_DIR/config-load.sh" "$ASSET_UPSTREAM/scripts/lib/"
    _asset_commit
    echo '{"version":1,"profiles":{"mine":{"engine":"codex"}}}' > "$ASSET_INSTALL/agent-profiles.json"
    echo mine > "$ASSET_INSTALL/.agent-profile"
    echo 'AGENT_ENGINE_PROFILES=true' > "$ASSET_INSTALL/config.env"
    cp "$ASSET_INSTALL/agent-profiles.json" "$TEST_TEMP_DIR/catalog"
    run bash "$SCRIPTS_DIR/update.sh" --yes "$ASSET_INSTALL"
    assert_success
    cmp "$TEST_TEMP_DIR/catalog" "$ASSET_INSTALL/agent-profiles.json"
    [ "$(cat "$ASSET_INSTALL/.agent-profile")" = mine ]
    [ "$(cat "$ASSET_INSTALL/config.env")" = AGENT_ENGINE_PROFILES=true ]
    for file in agent-profiles.example.json scripts/agent-profile.sh scripts/lib/named-profiles.sh scripts/lib/config-load.sh; do
        cmp "$ASSET_UPSTREAM/$file" "$ASSET_INSTALL/$file"
        grep -F "$file:" "$ASSET_INSTALL/.upstream"
    done
}

@test "named profiles: repeated standalone setup preserves adopted config catalog and selection" {
    _asset_fixture
    cp "$SCRIPTS_DIR/setup.sh" "$ASSET_UPSTREAM/scripts/"
    cp "$SCRIPTS_DIR/../agent-profiles.example.json" "$ASSET_UPSTREAM/"
    cp "$LIB_DIR/config-vars.sh" "$ASSET_UPSTREAM/scripts/lib/"
    cp "$SCRIPTS_DIR/../config.defaults.env.example" "$ASSET_UPSTREAM/"
    printf '#!/bin/bash\nexit 0\n' > "$ASSET_UPSTREAM/scripts/check-prereqs.sh"
    local target="$TEST_TEMP_DIR/consumer"
    mkdir -p "$target/.sandbox-pal-dispatch"
    printf 'AGENT_ENGINE_PROFILES=true\nAGENT_PROFILE=mine\n' > "$target/.sandbox-pal-dispatch/config.env"
    echo '{"version":1,"profiles":{"mine":{"engine":"codex"}}}' > "$target/.sandbox-pal-dispatch/agent-profiles.json"
    echo mine > "$target/.sandbox-pal-dispatch/.agent-profile"
    cp "$target/.sandbox-pal-dispatch/config.env" "$TEST_TEMP_DIR/before"
    printf '1\nowner/repo\ntest-bot\nmain\n\n\n%s\nn\nn\n' "$target" > "$TEST_TEMP_DIR/answers"
    run bash -c 'bash "$1/scripts/setup.sh" < "$2"' _ "$ASSET_UPSTREAM" "$TEST_TEMP_DIR/answers"
    assert_success
    cmp "$TEST_TEMP_DIR/before" "$target/.sandbox-pal-dispatch/config.env"
    [ "$(cat "$target/.sandbox-pal-dispatch/.agent-profile")" = mine ]
    jq -e '.profiles.mine.engine == "codex"' "$target/.sandbox-pal-dispatch/agent-profiles.json"
    grep -F 'agent-profiles.example.json:' "$target/.sandbox-pal-dispatch/.upstream"
    grep -qx '  - AGENT_PROFILE' "$target/.sandbox-pal-dispatch/.upstream"
}

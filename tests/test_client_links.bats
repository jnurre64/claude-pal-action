#!/usr/bin/env bats
load 'helpers/test_helper'

_client_fixture() {
    PROJECT="$TEST_TEMP_DIR/consumer repo"
    RUNTIME="$TEST_TEMP_DIR/runtime repo"
    mkdir -p "$PROJECT" "$RUNTIME/scripts"
    echo '# fixture dispatcher' > "$RUNTIME/scripts/sandbox-pal-dispatch.sh"
    for skill in sp-work sp-status sp-revise sp-post-merge; do
        mkdir -p "$RUNTIME/.claude/skills/$skill"
        cp "$SCRIPTS_DIR/../.claude/skills/$skill/SKILL.md" "$RUNTIME/.claude/skills/$skill/"
    done
}

@test "client links: reference runtime remains external and both clients share its skills" {
    _client_fixture
    echo custom > "$PROJECT/AGENTS.md"
    run bash "$SCRIPTS_DIR/link-client-skills.sh" "$PROJECT" "$RUNTIME"
    assert_success
    assert_output --partial 'Keep the .sandbox-pal-dispatch link local'
    [ "$(readlink "$PROJECT/.sandbox-pal-dispatch")" = '../runtime repo' ]
    for client in .claude .agents; do
        cmp "$RUNTIME/.claude/skills/sp-work/SKILL.md" "$PROJECT/$client/skills/sp-work/SKILL.md"
    done
    [ "$(cat "$PROJECT/AGENTS.md")" = custom ]
    echo updated >> "$RUNTIME/.claude/skills/sp-work/SKILL.md"
    cmp "$RUNTIME/.claude/skills/sp-work/SKILL.md" "$PROJECT/.agents/skills/sp-work/SKILL.md"
    rm "$PROJECT/.agents/skills/sp-status"
    run bash "$SCRIPTS_DIR/link-client-skills.sh" "$PROJECT" "$RUNTIME"
    assert_success
    [ -f "$PROJECT/.agents/skills/sp-status/SKILL.md" ]
}

@test "client links: custom runtime inside consumer survives moving the repository" {
    _client_fixture
    mkdir -p "$PROJECT/tools"
    mv "$RUNTIME" "$PROJECT/tools/worker runtime"
    RUNTIME="$PROJECT/tools/worker runtime"
    run bash "$SCRIPTS_DIR/link-client-skills.sh" "$PROJECT" "$RUNTIME"
    assert_success
    assert_output --partial 'inside the project'
    [ "$(readlink "$PROJECT/.sandbox-pal-dispatch")" = 'tools/worker runtime' ]
    mv "$PROJECT" "$TEST_TEMP_DIR/moved consumer"
    [ -f "$TEST_TEMP_DIR/moved consumer/.agents/skills/sp-work/SKILL.md" ]
    [ -f "$TEST_TEMP_DIR/moved consumer/.sandbox-pal-dispatch/scripts/sandbox-pal-dispatch.sh" ]
}

@test "client links: conflicting installation and missing runtime assets fail before linking" {
    _client_fixture
    ln -s missing-install "$PROJECT/.sandbox-pal-dispatch"
    run bash "$SCRIPTS_DIR/link-client-skills.sh" "$PROJECT" "$RUNTIME"
    assert_failure
    [ "$(readlink "$PROJECT/.sandbox-pal-dispatch")" = missing-install ]
    [ ! -e "$PROJECT/.agents" ]
    rm "$PROJECT/.sandbox-pal-dispatch" "$RUNTIME/.claude/skills/sp-work/SKILL.md"
    run bash "$SCRIPTS_DIR/link-client-skills.sh" "$PROJECT" "$RUNTIME"
    assert_failure
    assert_output --partial 'missing shared skill'
    [ ! -L "$PROJECT/.sandbox-pal-dispatch" ]
}

@test "client links: explicit connection preserves existing client skills" {
    _client_fixture
    mkdir -p "$PROJECT/.agents/skills/sp-work"
    echo custom > "$PROJECT/.agents/skills/sp-work/SKILL.md"
    run bash "$SCRIPTS_DIR/link-client-skills.sh" "$PROJECT" "$RUNTIME"
    assert_success
    assert_output --partial 'Preserved'
    [ "$(cat "$PROJECT/.agents/skills/sp-work/SKILL.md")" = custom ]
}

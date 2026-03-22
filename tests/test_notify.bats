#!/usr/bin/env bats
# Tests for scripts/lib/notify.sh

load 'helpers/test_helper'

_source_notify() {
    source "${LIB_DIR}/notify.sh"
}

# ===================================================================
# No-op behavior when unconfigured
# ===================================================================

@test "notify: silently no-ops when AGENT_NOTIFY_DISCORD_WEBHOOK is empty" {
    export AGENT_NOTIFY_DISCORD_WEBHOOK=""
    _source_notify

    run notify "plan_posted" "Test Issue" "https://github.com/test/1" "Plan summary"
    assert_success
    assert_output ""
}

@test "notify: silently no-ops when AGENT_NOTIFY_DISCORD_WEBHOOK is unset" {
    unset AGENT_NOTIFY_DISCORD_WEBHOOK
    _source_notify

    run notify "plan_posted" "Test Issue" "https://github.com/test/1" "Plan summary"
    assert_success
    assert_output ""
}

# ===================================================================
# Notification level filtering
# ===================================================================

@test "notify level 'actionable': sends plan_posted" {
    export AGENT_NOTIFY_DISCORD_WEBHOOK="https://discord.com/api/webhooks/test/token"
    export AGENT_NOTIFY_LEVEL="actionable"
    _source_notify

    run _notify_should_send "plan_posted"
    assert_success
}

@test "notify level 'actionable': skips implement_started" {
    export AGENT_NOTIFY_DISCORD_WEBHOOK="https://discord.com/api/webhooks/test/token"
    export AGENT_NOTIFY_LEVEL="actionable"
    _source_notify

    run _notify_should_send "implement_started"
    assert_failure
}

@test "notify level 'actionable': skips tests_passed" {
    export AGENT_NOTIFY_DISCORD_WEBHOOK="https://discord.com/api/webhooks/test/token"
    export AGENT_NOTIFY_LEVEL="actionable"
    _source_notify

    run _notify_should_send "tests_passed"
    assert_failure
}

@test "notify level 'actionable': sends agent_failed" {
    export AGENT_NOTIFY_DISCORD_WEBHOOK="https://discord.com/api/webhooks/test/token"
    export AGENT_NOTIFY_LEVEL="actionable"
    _source_notify

    run _notify_should_send "agent_failed"
    assert_success
}

@test "notify level 'failures': sends tests_failed" {
    export AGENT_NOTIFY_LEVEL="failures"
    _source_notify

    run _notify_should_send "tests_failed"
    assert_success
}

@test "notify level 'failures': sends agent_failed" {
    export AGENT_NOTIFY_LEVEL="failures"
    _source_notify

    run _notify_should_send "agent_failed"
    assert_success
}

@test "notify level 'failures': skips plan_posted" {
    export AGENT_NOTIFY_LEVEL="failures"
    _source_notify

    run _notify_should_send "plan_posted"
    assert_failure
}

@test "notify level 'failures': skips pr_created" {
    export AGENT_NOTIFY_LEVEL="failures"
    _source_notify

    run _notify_should_send "pr_created"
    assert_failure
}

@test "notify level 'all': sends implement_started" {
    export AGENT_NOTIFY_LEVEL="all"
    _source_notify

    run _notify_should_send "implement_started"
    assert_success
}

@test "notify level 'all': sends tests_passed" {
    export AGENT_NOTIFY_LEVEL="all"
    _source_notify

    run _notify_should_send "tests_passed"
    assert_success
}

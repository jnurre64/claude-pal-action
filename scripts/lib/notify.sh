#!/bin/bash
# ─── Discord notification layer (optional) ─────────────────────────
# Sends Discord webhook notifications at dispatch milestones.
# Silently no-ops if AGENT_NOTIFY_DISCORD_WEBHOOK is not configured.

# ─── Notification level check ──────────────────────────────────────
# Returns 0 (true) if the event should be sent at the current level.
_notify_should_send() {
    local event_type="$1"
    local level="${AGENT_NOTIFY_LEVEL:-actionable}"

    case "$level" in
        all)
            return 0
            ;;
        actionable)
            case "$event_type" in
                plan_posted|questions_asked|pr_created|review_feedback|agent_failed)
                    return 0 ;;
                *)
                    return 1 ;;
            esac
            ;;
        failures)
            case "$event_type" in
                tests_failed|agent_failed)
                    return 0 ;;
                *)
                    return 1 ;;
            esac
            ;;
        *)
            return 0
            ;;
    esac
}

# ─── Event metadata ────────────────────────────────────────────────
_notify_event_color() {
    case "$1" in
        pr_created|tests_passed)     echo "5763719"  ;;  # green
        tests_failed|agent_failed)   echo "15548997" ;;  # red
        plan_posted|questions_asked) echo "3447003"  ;;  # blue
        review_feedback)             echo "16776960" ;;  # yellow
        *)                           echo "9807270"  ;;  # grey
    esac
}

_notify_event_label() {
    case "$1" in
        plan_posted)        echo "Plan Ready"             ;;
        questions_asked)    echo "Questions"              ;;
        implement_started)  echo "Implementation Started" ;;
        tests_passed)       echo "Tests Passed"           ;;
        tests_failed)       echo "Tests Failed"           ;;
        pr_created)         echo "PR Created"             ;;
        review_feedback)    echo "Review Feedback"        ;;
        agent_failed)       echo "Agent Failed"           ;;
        *)                  echo "Agent Update"           ;;
    esac
}

_notify_event_indicator() {
    case "$1" in
        pr_created|tests_passed)     echo "[OK]"     ;;
        tests_failed|agent_failed)   echo "[FAIL]"   ;;
        plan_posted|questions_asked) echo "[INFO]"   ;;
        review_feedback)             echo "[ACTION]" ;;
        implement_started)           echo "[INFO]"   ;;
        *)                           echo "[INFO]"   ;;
    esac
}

# ─── Build Discord embed JSON ──────────────────────────────────────
# Usage: _notify_build_embed <event_type> <title> <url> <description>
_notify_build_embed() {
    local event_type="$1"
    local title="$2"
    local url="$3"
    local description="$4"

    local color label indicator
    color=$(_notify_event_color "$event_type")
    label=$(_notify_event_label "$event_type")
    indicator=$(_notify_event_indicator "$event_type")

    # Truncate description to fit Discord embed limit (4096 chars, leave room for indicator)
    if [ "${#description}" -gt 4000 ]; then
        description="${description:0:3997}..."
    fi

    local embed_title="${indicator} ${label} -- #${NUMBER}: ${title}"

    # Build JSON with jq for proper escaping
    jq -n \
        --arg username "Agent Dispatch" \
        --arg title "$embed_title" \
        --arg url "$url" \
        --arg description "$description" \
        --argjson color "$color" \
        --arg footer "Automated by claude-agent-dispatch | ${REPO:-unknown} #${NUMBER:-0}" \
        --arg timestamp "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
        '{
            username: $username,
            embeds: [{
                title: $title,
                url: $url,
                description: $description,
                color: $color,
                footer: { text: $footer },
                timestamp: $timestamp
            }]
        }'
}

# ─── Main notification function ────────────────────────────────────
# Usage: notify <event_type> <title> <url> [description]
#
# Event types: plan_posted, questions_asked, implement_started,
#              tests_passed, tests_failed, pr_created,
#              review_feedback, agent_failed
notify() {
    local event_type="${1:-}"
    local title="${2:-}"
    local url="${3:-}"
    local description="${4:-}"

    # No-op if webhook not configured
    [ -z "${AGENT_NOTIFY_DISCORD_WEBHOOK:-}" ] && return 0

    # Check notification level filter
    _notify_should_send "$event_type" || return 0

    local json
    json=$(_notify_build_embed "$event_type" "$title" "$url" "$description")

    _notify_send "$json"
}

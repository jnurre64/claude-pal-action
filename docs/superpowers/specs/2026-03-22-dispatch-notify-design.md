# Dispatch Notify — Discord Notification & Interaction Layer

**Date:** 2026-03-22
**Status:** Approved design, pending implementation
**Scope:** Optional notification and two-way interaction layer for claude-agent-dispatch

## Overview

Add an optional Discord notification and interaction layer to the dispatch system. At each dispatch milestone (plan posted, PR created, tests failed, etc.), a notification is sent to a configured Discord channel. In Phase 2, interactive buttons and slash commands allow users to approve plans, request changes, post feedback, and manage agent work entirely from Discord — without ever opening GitHub.

The dispatch architecture (`claude -p`, one-shot, label-driven) is unchanged. This layer sits alongside it and communicates via GitHub labels and comments, which trigger the existing dispatch workflows.

### What it does NOT do

- Change how dispatch works — dispatch remains `claude -p` based
- Store conversation state — stateless mapping from Discord interactions to GitHub API
- Require Claude Code Channels, claude.ai login, or Anthropic API keys
- Read or process user messages (buttons + slash commands only in Phase 2)

## Phased Rollout

### Phase 1: Webhook Notification Layer

Send-only Discord notifications via webhook. No bot, no replies — just `curl` at milestones.

### Phase 2: Discord Bot with Buttons & Slash Commands

A lightweight Discord bot (~200 lines, `discord.py`) replaces the webhook. Adds interactive buttons on notifications and slash commands for managing agent work. A modal dialog collects free-text feedback for plan revisions and comments.

### Phase 3: Future Channel-Based Architecture (documented only)

When Claude Code Channels support `-p` mode or alternative auth, a persistent Claude session could replace the Discord bot as a natural-language coordinator. Not built now — documented as an evolution path.

## Milestone Events

| Event | Trigger point in dispatch | Notification level | Buttons (Phase 2) |
|---|---|---|---|
| Plan posted | `handle_new_issue` after plan comment | `actionable` | View Plan, Approve, Request Changes, Comment |
| Questions asked | `handle_new_issue` ask_questions branch | `actionable` | View Issue |
| Implementation started | `handle_implement` after label set | `all` | View Issue |
| Tests passed | `handle_post_implementation` after test gate | `all` | View Issue |
| Tests failed | `handle_post_implementation` after test gate fails | `failures` | View Issue |
| PR created | `handle_post_implementation` after PR created | `actionable` | View PR, View Issue |
| Review feedback received | `handle_pr_review` start | `actionable` | View PR |
| Agent failed | Any `set_label "agent:failed"` | `failures` | View Issue, Retry |

## Agent Notification Best Practices

These principles are baked into the design:

**Identity and transparency:**
- Bot/webhook username clearly identifies as automated: "Agent Dispatch"
- Every notification includes a footer: "Automated by claude-agent-dispatch"
- Never mimics a human — always clear this is automated output

**Signal over noise:**
- Configurable notification levels via `AGENT_NOTIFY_LEVEL`:
  - `all` — every milestone
  - `actionable` (default) — only events needing user response
  - `failures` — only failures
- Each notification tagged with urgency via text indicators, not color alone

**Context sufficiency:**
- Include enough information to make a decision without leaving Discord
- Truncate responsibly with "View full details" link to GitHub
- Always include issue/PR number prominently

**Idempotency:**
- Issue/PR number in embed footer for deduplication
- Timestamp on every notification

**Accessibility:**
- Text status indicators alongside colors (not color-only)
- Status indicators: check mark for success, X for failure, clipboard for plan, question mark for questions, arrows for in progress

**Rate awareness:**
- Discord webhook limit: 5 requests per 2 seconds (dispatch naturally stays well under)
- If circuit breaker fires, send one notification, not one per attempt

## Phase 1: Technical Design

### New file: `scripts/lib/notify.sh`

A `notify()` function that:
1. Accepts an event type and key-value data (title, URL, summary, etc.)
2. Checks `AGENT_NOTIFY_LEVEL` to decide whether to send
3. Formats a Discord embed (color-coded sidebar, fields, links, footer)
4. Sends via `curl` to the configured webhook URL
5. Silently no-ops if no webhook is configured

Embed colors by event type:
- Green: success (PR created, tests passed)
- Red: failure (tests failed, agent failed)
- Blue: informational (plan posted, questions asked)
- Yellow: action needed (review feedback)

### Changes to existing files

**`scripts/lib/common.sh`:**
- Source `notify.sh`
- Add `notify()` calls at each milestone

**`scripts/lib/defaults.sh`:**
- New config vars with empty defaults (feature disabled unless configured)

**`config.env.example`:**
- Document new vars with examples

### New configuration variables

```bash
# Discord webhook URL (Phase 1 — send-only notifications)
AGENT_NOTIFY_DISCORD_WEBHOOK=""

# Optional: post to a specific Discord thread
AGENT_NOTIFY_DISCORD_THREAD_ID=""

# Notification level: "all", "actionable" (default), "failures"
AGENT_NOTIFY_LEVEL="actionable"
```

### Design decisions

- **Embeds over plain text:** Support links/colors, embed description allows 4096 chars vs 2000-char message limit
- **Thread support optional:** Keeps agent notifications in a dedicated thread to avoid cluttering a channel
- **No retry logic:** If the webhook fails, log and move on. Agent work should not block on notification delivery
- **Truncation:** Plan summaries and test output truncated to fit Discord limits (4096 chars for embed description)

## Phase 2: Technical Design

### Discord bot architecture

**Framework:** `discord.py` (actively maintained, lightweight, well-suited for small bots)

**Process model:** Gateway bot running as a systemd service on the self-hosted runner. Outbound WebSocket connection only — no ports exposed publicly, no TLS certificates needed.

**Components (~200 lines total):**
1. Local HTTP listener (localhost only) — receives POST from dispatch scripts
2. Discord message sender — formats notification embeds with interactive buttons
3. Interaction handlers — buttons, modals, and slash commands
4. GitHub bridge — translates interactions to `gh` CLI calls

### Button interactions

Buttons encode action and issue number in `custom_id` (under Discord's 100-char limit):

| Button | custom_id | GitHub operation |
|---|---|---|
| Approve | `approve:42` | `gh issue edit 42 --remove-label agent:plan-review --add-label agent:plan-approved` |
| Request Changes | `changes:42` | Opens modal, posts comment to issue 42 |
| Comment | `comment:42` | Opens modal, posts comment to issue 42 |
| Retry | `retry:42` | Removes agent labels, adds `agent` label |
| View Plan / View PR | URL buttons | Direct links to GitHub (no custom_id, no handler needed) |

Buttons are created with `timeout=None` for persistence — they remain functional on messages that are hours or days old.

### Interaction lifecycle

1. Button click or slash command received
2. Verify user is in allowed role/user list (ephemeral rejection if not)
3. Defer response (shows "thinking..." — `gh` CLI calls may take >3 seconds)
4. Execute `gh` command
5. Edit original message: disable action buttons, add status line (e.g., "Approved by @jonny")
6. Send ephemeral follow-up confirmation (only the clicker sees it)

### Slash commands

Registered as guild commands for instant availability:

| Command | Description | GitHub operation |
|---|---|---|
| `/approve <issue>` | Approve a plan | `gh issue edit N --add-label agent:plan-approved` |
| `/reject <issue> [reason]` | Reject with reason | Comment + `agent:failed` label |
| `/comment <issue> <text>` | Post feedback | `gh issue comment N` |
| `/status [issue]` | Check agent status | Reads labels, shows current state |
| `/retry <issue>` | Re-trigger agent | Removes labels, adds `agent` label |

### Modal for free-text feedback

Triggered by Request Changes or Comment buttons. Multi-line text input, 10-2000 characters. Text is sanitized before passing to `gh issue comment` to prevent shell injection.

The comment is posted to the GitHub issue, which triggers the existing `dispatch-reply.yml` workflow. The agent's response flows back through the normal dispatch cycle and appears as a new Discord notification.

### Full conversation loop

```
Discord: [Plan posted notification] -> User clicks [Request Changes] -> types feedback
  |
GitHub: Comment posted on issue -> dispatch-reply triggers -> agent re-triages
  |
Discord: [Updated plan notification] -> User clicks [Approve]
  |
GitHub: Label added -> dispatch-implement triggers -> agent implements
  |
Discord: [PR created notification] -> User clicks [View PR]
```

### Security

- **User allowlist:** `AGENT_DISCORD_ALLOWED_USERS` (Discord user IDs) or `AGENT_DISCORD_ALLOWED_ROLE` (role ID). Only listed users/roles can click action buttons. View/link buttons work for anyone.
- **Ephemeral rejections:** Unauthorized clicks get a private "you don't have permission" message
- **Audit logging:** Every action logged with timestamp, Discord user, issue number, action
- **Token in env var:** Never committed, loaded from `config.env`
- **Local API on localhost only:** `127.0.0.1:PORT`, not exposed externally
- **Input sanitization:** Modal text sanitized before passing to `gh` commands
- **No message content intent:** Bot uses only the Interactions API
- **Minimal permissions:** `View Channels` + `Send Messages` in the target channel only

### Process management

Systemd service with `Restart=on-failure`, `RestartSec=10`, `TimeoutStopSec=30`. Runs as the same user as the dispatch runner.

### Phase 1 to Phase 2 transition

- `notify()` function gets a second backend: `curl` to `localhost:BOT_PORT/notify` instead of Discord webhook
- Same JSON payload structure — the bot adds buttons before sending
- Config toggle: `AGENT_NOTIFY_BACKEND="webhook"` (Phase 1) or `AGENT_NOTIFY_BACKEND="bot"` (Phase 2)
- Webhook mode remains as fallback if bot is down

### New configuration variables (Phase 2)

```bash
# Discord Bot (replaces webhook for interactive notifications)
AGENT_DISCORD_BOT_TOKEN=""
AGENT_DISCORD_CHANNEL_ID=""
AGENT_DISCORD_ALLOWED_USERS=""       # Comma-separated Discord user IDs
AGENT_DISCORD_ALLOWED_ROLE=""        # Or a Discord role ID
AGENT_DISCORD_BOT_PORT="8675"        # Local API port for dispatch -> bot
AGENT_NOTIFY_BACKEND="webhook"       # "webhook" (Phase 1) or "bot" (Phase 2)
```

### Discord compliance

- Webhook rate limit (5 req/2 sec) respected; dispatch naturally stays well under
- Bot requires no privileged intents (no message content intent)
- Public privacy policy required: "This bot processes Discord button clicks and slash commands to manage GitHub issues. No user data is collected or stored."
- Bot permissions follow principle of least privilege: `View Channels` + `Send Messages` only
- No automated messages for activity inflation — all notifications are genuine operational events

### Alternative: HTTP Interactions Endpoint (documented, not built)

For reference-mode users deploying to cloud infrastructure, Discord's HTTP Interactions Endpoint eliminates the persistent bot process. Discord POSTs interactions to a public HTTPS URL, enabling serverless deployment (Lambda, Cloud Functions). Requires public endpoint with TLS — not suitable for self-hosted runners behind firewalls but documented as an alternative architecture.

## Phase 3: Future Channel-Based Architecture

**Status:** Not built. Documented as evolution path.

**Trigger to revisit:** Any of these changes from Anthropic:
- Channels work with `claude -p` (headless mode)
- Channels support API key or subscription-based auth (not just claude.ai login)
- A stable (non-research-preview) release of Channels with a settled API contract

**What it would look like:**
- A custom webhook channel (MCP server) receives GitHub events and dispatch notifications
- Claude in a persistent session acts as coordinator — receives events, reasons about them, communicates via Discord/Telegram
- Implementation still happens via `claude -p` dispatch
- The coordinator replaces the Phase 2 Discord bot — Claude handles natural language instead of button/command mapping

**What it would enable beyond Phase 2:**
- Natural conversation with the agent ("what's taking so long on issue 42?")
- Proactive context surfacing ("Issue #42 is similar to #31 — same approach?")
- Multi-platform simultaneously (Discord + Telegram from one session)

**Preparation (built into Phases 1-2):**
- `notify()` interface is generic — structured data, not Discord-specific payloads
- GitHub labels and comments remain the source of truth for dispatch state
- No Discord-only state introduced

## File Structure

```
claude-agent-dispatch/
  scripts/
    lib/
      notify.sh                    # NEW - notification layer
  discord-bot/                     # NEW - Phase 2
    bot.py                         # Main bot (~200 lines)
    requirements.txt               # discord.py
    install.sh                     # Sets up venv + systemd service
    README.md                      # Setup guide
  docs/
    notifications.md               # NEW - setup guide for Phase 1 + 2
    future-channels.md             # NEW - Phase 3 roadmap documentation
  config.env.example               # UPDATED - new notification vars
  tests/
    notify.bats                    # NEW - Phase 1 tests
```

## Testing Strategy

### Phase 1 tests (BATS)

- `notify()` with no config set: silent no-op, no errors
- `notify()` with webhook configured: correct curl arguments (mock curl)
- Embed formatting: correct JSON structure, truncation at limits, color mapping
- Notification level filtering: `actionable` skips status-only, `failures` skips non-failures
- Thread ID inclusion when configured
- All milestone events produce correctly structured payloads

### Phase 2 tests

- Bot local API: correct Discord embed + button payloads
- Button custom_id parsing: correct action and issue number extraction
- User allowlist: authorized users proceed, unauthorized get ephemeral rejection
- Modal text: properly sanitized before `gh` command execution
- Slash command argument validation: handles missing/invalid issue numbers
- Fallback to webhook when bot is unavailable
- Integration test: button click -> `gh` CLI call (mock `gh`)

### Manual testing checklist

- Send test notification via webhook (Phase 1)
- Click each button type, verify GitHub label/comment changes
- Test each slash command
- Submit modal with special characters (quotes, backticks, newlines)
- Test with unauthorized Discord user
- Kill bot process, verify dispatch still works (fallback to webhook or no-op)
- Verify buttons on old messages (hours old) still work

## Anthropic Usage Policy Compliance

This design is compliant with Anthropic's Usage Policy (updated September 2025):
- Forwarding agent output to messaging platforms is permitted
- Official Claude Code Channel plugins for Discord/Telegram demonstrate Anthropic endorses this pattern
- Access controls (sender allowlists) are implemented
- Automated notifications are genuine operational events, not spam or engagement manipulation
- AI agent involvement is disclosed in notification footers

## Future: Telegram Support

Telegram is planned as a secondary platform. The `notify()` function's generic interface supports adding a Telegram backend without changing the dispatch scripts. Telegram Bot API is simpler than Discord for send-only notifications (single `curl` POST), and polling-based reply handling avoids the need for a public endpoint. This will be designed and specced separately when Discord support is stable.

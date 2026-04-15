# Slack Bot (Phase 2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Slack bot for claude-agent-dispatch that receives notifications via local HTTP, posts interactive Block Kit messages to Slack, and handles button actions, modal dialogs, and slash commands that drive GitHub issue workflows.

**Architecture:** The bot connects to Slack via Socket Mode (outbound WebSocket, no public URL) and runs a local aiohttp HTTP server on `127.0.0.1:8676` for receiving dispatch notifications. Button clicks and slash commands call `gh` CLI to manage GitHub issue labels and post comments, same as the existing Discord bot. Both bots import shared logic from `shared/dispatch_bot/`.

**Tech Stack:** Python 3.10+, `slack-bolt` (async), `slack-sdk`, `aiohttp`, `shared/dispatch_bot/`

---

## Research Summary

Best practices research confirmed these key decisions:

- **Python + slack-bolt**: Official Slack SDK, first-class async support, matches existing Discord bot language. No reason to switch to Go/Node for a human-speed interaction bot.
- **Socket Mode**: Correct choice for self-hosted deployment with no public endpoints. Outbound WebSocket only (port 443), no TLS cert management, no request signature verification needed.
- **AsyncApp**: Required to share the asyncio event loop with aiohttp (our local HTTP notification server).
- **Attachments with color + blocks**: The standard way to get colored sidebar on Slack messages. Top-level blocks don't support color.
- **action_id for routing, value for context**: Slack buttons use `action_id` to identify which action (approve, retry, etc.) and `value` to carry data (`repo:issue_number`).
- **private_metadata on modals**: JSON-encoded string (max 3000 chars) carries context (repo, issue, channel, ts) through the modal lifecycle.
- **Always ack() first**: Slack requires acknowledgment within 3 seconds; do work after acking.
- **Scopes**: `chat:write`, `commands`, `connections:write`. Add `usergroups:read` only if `AGENT_SLACK_ALLOWED_GROUP` is used.

## File Structure

| File | Responsibility |
|---|---|
| `slack-bot/bot.py` | Main bot: config, Block Kit builders, button handlers, modal flow, slash commands, HTTP handler, entrypoint |
| `slack-bot/requirements.txt` | Dependencies: slack-bolt, slack-sdk, aiohttp, shared package |
| `slack-bot/install.sh` | Install script: venv, deps, systemd service setup |
| `slack-bot/agent-dispatch-slack.service` | systemd unit file template |
| `slack-bot/CLAUDE.md` | Development context for AI agents |
| `slack-bot/README.md` | Setup guide: create Slack app, configure tokens, install |
| `slack-bot/tests/conftest.py` | Test path setup |
| `slack-bot/tests/test_blocks.py` | Tests for build_blocks, build_actions |
| `slack-bot/tests/test_utils.py` | Tests for parse_value, is_authorized, build_updated_attachments |
| `slack-bot/tests/test_interactions.py` | Tests for button handlers and modal submission |
| `slack-bot/tests/test_commands.py` | Tests for slash commands |
| `slack-bot/tests/test_http.py` | Tests for notification HTTP handler |

---

### Task 1: Project Scaffolding

**Files:**
- Create: `slack-bot/requirements.txt`
- Create: `slack-bot/tests/conftest.py`
- Create: `slack-bot/bot.py` (config and imports only)

- [ ] **Step 1: Create requirements.txt**

```
slack-bolt>=1.18,<2
slack-sdk>=3.27,<4
aiohttp>=3.9,<4
-e ../shared
```

- [ ] **Step 2: Create tests/conftest.py**

```python
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
```

- [ ] **Step 3: Create bot.py with config and imports**

```python
"""Slack bot for claude-agent-dispatch interactive notifications."""

import json
import logging
import os

from aiohttp import web

from dispatch_bot.events import (
    EVENT_INDICATORS,
    EVENT_LABELS,
    PLAN_EVENTS,
    RETRY_EVENTS,
)
from dispatch_bot.github import ALL_AGENT_LABELS, gh_command, gh_dispatch
from dispatch_bot.auth import is_authorized_check
from dispatch_bot.sanitize import sanitize_input
from dispatch_bot.http_listener import start_http_server

log = logging.getLogger("dispatch-bot")

# --- Configuration (from environment) ---
BOT_TOKEN = os.environ.get("AGENT_SLACK_BOT_TOKEN", "")
APP_TOKEN = os.environ.get("AGENT_SLACK_APP_TOKEN", "")
CHANNEL_ID = os.environ.get("AGENT_SLACK_CHANNEL_ID", "")
ALLOWED_USERS = set(os.environ.get("AGENT_SLACK_ALLOWED_USERS", "").split(",")) - {""}
ALLOWED_GROUP = os.environ.get("AGENT_SLACK_ALLOWED_GROUP", "")
BOT_PORT = int(os.environ.get("AGENT_SLACK_BOT_PORT", "8676"))
DEFAULT_REPO = os.environ.get("AGENT_DISPATCH_REPO", "")

# --- Event colors (hex strings for Slack attachment sidebar) ---
EVENT_COLORS: dict[str, str] = {
    "pr_created": "#57F287", "tests_passed": "#57F287", "review_pushed": "#57F287",
    "tests_failed": "#ED4245", "agent_failed": "#ED4245",
    "plan_posted": "#3498DB", "questions_asked": "#3498DB",
    "review_feedback": "#FFFF00",
}
```

- [ ] **Step 4: Create venv and install dependencies**

Run:
```bash
cd slack-bot && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```
Expected: Install completes with no errors.

- [ ] **Step 5: Verify imports work**

Run:
```bash
cd slack-bot && .venv/bin/python -c "import bot; print('OK')"
```
Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add slack-bot/bot.py slack-bot/requirements.txt slack-bot/tests/conftest.py
git commit -m "feat(slack-bot): add project scaffolding"
```

---

### Task 2: Block Kit Message Builders (TDD)

**Files:**
- Create: `slack-bot/tests/test_blocks.py`
- Modify: `slack-bot/bot.py` (add `build_blocks`, `build_actions`)

- [ ] **Step 1: Write test_blocks.py**

```python
from bot import build_blocks, build_actions, EVENT_COLORS


class TestBuildBlocks:
    def test_plan_posted_title_includes_indicator_and_label(self):
        blocks = build_blocks("plan_posted", "Add caching", "https://github.com/r/1", "Plan here", 42, "org/repo")
        title_text = blocks[0]["text"]["text"]
        assert "[INFO]" in title_text
        assert "Plan Ready" in title_text

    def test_title_includes_issue_number_as_link(self):
        blocks = build_blocks("plan_posted", "My Issue", "https://example.com", "desc", 42, "org/repo")
        title_text = blocks[0]["text"]["text"]
        assert "#42" in title_text
        assert "<https://example.com|" in title_text

    def test_description_included_as_section(self):
        blocks = build_blocks("plan_posted", "T", "https://x.com", "Plan details here", 1, "r")
        texts = [b["text"]["text"] for b in blocks if b["type"] == "section"]
        assert any("Plan details here" in t for t in texts)

    def test_description_truncated_at_3000(self):
        long_desc = "x" * 4000
        blocks = build_blocks("plan_posted", "T", "https://x.com", long_desc, 1, "r")
        desc_block = [b for b in blocks if b["type"] == "section" and "x" * 100 in b["text"]["text"]][0]
        assert len(desc_block["text"]["text"]) <= 3000

    def test_empty_description_omits_section(self):
        blocks = build_blocks("tests_passed", "T", "https://x.com", "", 1, "r")
        section_blocks = [b for b in blocks if b["type"] == "section"]
        assert len(section_blocks) == 1  # only the title section

    def test_footer_includes_automation_disclosure(self):
        blocks = build_blocks("plan_posted", "T", "https://x.com", "d", 1, "org/repo")
        context = [b for b in blocks if b["type"] == "context"][0]
        assert "Automated by claude-agent-dispatch" in context["elements"][0]["text"]

    def test_footer_includes_repo_and_issue(self):
        blocks = build_blocks("plan_posted", "T", "https://x.com", "d", 42, "org/repo")
        context = [b for b in blocks if b["type"] == "context"][0]
        assert "org/repo #42" in context["elements"][0]["text"]

    def test_unknown_event_gets_info_indicator(self):
        blocks = build_blocks("unknown_event", "T", "https://x.com", "d", 1, "r")
        title_text = blocks[0]["text"]["text"]
        assert "[INFO]" in title_text

    def test_all_blocks_use_mrkdwn(self):
        blocks = build_blocks("plan_posted", "T", "https://x.com", "desc", 1, "r")
        for b in blocks:
            if b["type"] == "section":
                assert b["text"]["type"] == "mrkdwn"


class TestBuildActions:
    def test_plan_posted_has_approve_changes_comment(self):
        actions = build_actions("plan_posted", 42, "https://example.com", "org/repo")
        elements = actions[0]["elements"]
        action_ids = [e.get("action_id") for e in elements]
        assert "approve" in action_ids
        assert "changes" in action_ids
        assert "comment" in action_ids

    def test_plan_posted_has_view_link(self):
        actions = build_actions("plan_posted", 42, "https://example.com", "org/repo")
        elements = actions[0]["elements"]
        link_buttons = [e for e in elements if e.get("url")]
        assert len(link_buttons) >= 1
        assert link_buttons[0]["url"] == "https://example.com"

    def test_agent_failed_has_retry(self):
        actions = build_actions("agent_failed", 42, "https://example.com", "org/repo")
        elements = actions[0]["elements"]
        action_ids = [e.get("action_id") for e in elements]
        assert "retry" in action_ids

    def test_agent_failed_no_approve(self):
        actions = build_actions("agent_failed", 42, "https://example.com", "org/repo")
        elements = actions[0]["elements"]
        action_ids = [e.get("action_id") for e in elements]
        assert "approve" not in action_ids

    def test_tests_passed_view_only(self):
        actions = build_actions("tests_passed", 42, "https://example.com", "org/repo")
        elements = actions[0]["elements"]
        action_buttons = [e for e in elements if not e.get("url")]
        assert len(action_buttons) == 0

    def test_values_encode_repo_and_issue(self):
        actions = build_actions("plan_posted", 99, "https://example.com", "org/repo")
        elements = actions[0]["elements"]
        values = [e.get("value") for e in elements if e.get("value")]
        assert all(v == "org/repo:99" for v in values)

    def test_approve_button_has_primary_style(self):
        actions = build_actions("plan_posted", 42, "https://example.com", "org/repo")
        elements = actions[0]["elements"]
        approve = [e for e in elements if e.get("action_id") == "approve"][0]
        assert approve["style"] == "primary"

    def test_changes_button_has_danger_style(self):
        actions = build_actions("plan_posted", 42, "https://example.com", "org/repo")
        elements = actions[0]["elements"]
        changes = [e for e in elements if e.get("action_id") == "changes"][0]
        assert changes["style"] == "danger"

    def test_returns_list_with_actions_block(self):
        actions = build_actions("plan_posted", 42, "https://example.com", "org/repo")
        assert len(actions) == 1
        assert actions[0]["type"] == "actions"


class TestEventColors:
    def test_success_events_are_green(self):
        for event in ("pr_created", "tests_passed", "review_pushed"):
            assert EVENT_COLORS[event] == "#57F287"

    def test_failure_events_are_red(self):
        for event in ("tests_failed", "agent_failed"):
            assert EVENT_COLORS[event] == "#ED4245"

    def test_info_events_are_blue(self):
        for event in ("plan_posted", "questions_asked"):
            assert EVENT_COLORS[event] == "#3498DB"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd slack-bot && .venv/bin/python -m pytest tests/test_blocks.py -v`
Expected: FAIL with `ImportError: cannot import name 'build_blocks'`

- [ ] **Step 3: Add build_blocks and build_actions to bot.py**

Append to `slack-bot/bot.py`:

```python


def build_blocks(
    event_type: str, title: str, url: str, description: str, issue_number: int, repo: str,
) -> list[dict]:
    """Build Block Kit blocks for notification content."""
    indicator = EVENT_INDICATORS.get(event_type, "[INFO]")
    label = EVENT_LABELS.get(event_type, "Agent Update")

    blocks: list[dict] = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{indicator} {label} -- <{url}|#{issue_number}: {title}>*",
            },
        },
    ]
    if description:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": description[:3000]},
        })
    blocks.append({
        "type": "context",
        "elements": [
            {"type": "mrkdwn", "text": f"Automated by claude-agent-dispatch | {repo} #{issue_number}"},
        ],
    })
    return blocks


def build_actions(event_type: str, issue_number: int, url: str, repo: str) -> list[dict]:
    """Build action button elements for a notification."""
    value = f"{repo}:{issue_number}"
    elements: list[dict] = [
        {
            "type": "button",
            "text": {"type": "plain_text", "text": "View"},
            "url": url,
            "action_id": "view_link",
        },
    ]
    if event_type in PLAN_EVENTS:
        elements.extend([
            {"type": "button", "text": {"type": "plain_text", "text": "Approve"}, "action_id": "approve", "value": value, "style": "primary"},
            {"type": "button", "text": {"type": "plain_text", "text": "Request Changes"}, "action_id": "changes", "value": value, "style": "danger"},
            {"type": "button", "text": {"type": "plain_text", "text": "Comment"}, "action_id": "comment", "value": value},
        ])
    elif event_type in RETRY_EVENTS:
        elements.append(
            {"type": "button", "text": {"type": "plain_text", "text": "Retry"}, "action_id": "retry", "value": value, "style": "primary"},
        )
    return [{"type": "actions", "elements": elements}]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd slack-bot && .venv/bin/python -m pytest tests/test_blocks.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add slack-bot/bot.py slack-bot/tests/test_blocks.py
git commit -m "feat(slack-bot): add Block Kit message builders"
```

---

### Task 3: Utilities -- parse_value, is_authorized, build_updated_attachments (TDD)

**Files:**
- Create: `slack-bot/tests/test_utils.py`
- Modify: `slack-bot/bot.py` (add utility functions)

- [ ] **Step 1: Write test_utils.py**

```python
from unittest.mock import AsyncMock, patch

import pytest

from bot import parse_value, is_authorized, build_updated_attachments


class TestParseValue:
    def test_parses_repo_and_issue(self):
        repo, issue = parse_value("org/repo:42")
        assert repo == "org/repo"
        assert issue == 42

    def test_parses_repo_with_hyphens(self):
        repo, issue = parse_value("Frightful-Games/recipe-manager-demo:7")
        assert repo == "Frightful-Games/recipe-manager-demo"
        assert issue == 7

    def test_returns_none_for_no_colon(self):
        repo, issue = parse_value("invalid")
        assert repo is None
        assert issue is None

    def test_returns_none_for_non_numeric_issue(self):
        repo, issue = parse_value("org/repo:abc")
        assert repo is None
        assert issue is None

    def test_returns_none_for_empty_string(self):
        repo, issue = parse_value("")
        assert repo is None
        assert issue is None

    def test_handles_multiple_colons_in_repo(self):
        # rsplit on last colon, so "a:b:42" -> repo="a:b", issue=42
        repo, issue = parse_value("a:b:42")
        assert repo == "a:b"
        assert issue == 42


class TestIsAuthorized:
    @pytest.mark.asyncio
    async def test_user_in_allowed_list(self):
        client = AsyncMock()
        with patch("bot.ALLOWED_USERS", {"U123", "U456"}), patch("bot.ALLOWED_GROUP", ""):
            assert await is_authorized("U123", client) is True

    @pytest.mark.asyncio
    async def test_user_not_in_allowed_list(self):
        client = AsyncMock()
        with patch("bot.ALLOWED_USERS", {"U123"}), patch("bot.ALLOWED_GROUP", ""):
            assert await is_authorized("U999", client) is False

    @pytest.mark.asyncio
    async def test_user_in_allowed_group(self):
        client = AsyncMock()
        client.usergroups_users_list = AsyncMock(return_value={"users": ["U456", "U789"]})
        with patch("bot.ALLOWED_USERS", set()), patch("bot.ALLOWED_GROUP", "G100"):
            assert await is_authorized("U456", client) is True

    @pytest.mark.asyncio
    async def test_user_not_in_allowed_group(self):
        client = AsyncMock()
        client.usergroups_users_list = AsyncMock(return_value={"users": ["U456"]})
        with patch("bot.ALLOWED_USERS", set()), patch("bot.ALLOWED_GROUP", "G100"):
            assert await is_authorized("U999", client) is False

    @pytest.mark.asyncio
    async def test_no_restrictions_denies_all(self):
        client = AsyncMock()
        with patch("bot.ALLOWED_USERS", set()), patch("bot.ALLOWED_GROUP", ""):
            assert await is_authorized("U123", client) is False

    @pytest.mark.asyncio
    async def test_group_api_failure_denies(self):
        client = AsyncMock()
        client.usergroups_users_list = AsyncMock(side_effect=Exception("API error"))
        with patch("bot.ALLOWED_USERS", set()), patch("bot.ALLOWED_GROUP", "G100"):
            assert await is_authorized("U456", client) is False


class TestBuildUpdatedAttachments:
    def _make_message(self):
        return {
            "text": "fallback",
            "attachments": [{
                "color": "#3498DB",
                "blocks": [
                    {"type": "section", "text": {"type": "mrkdwn", "text": "*title*"}},
                    {"type": "actions", "elements": [
                        {"type": "button", "text": {"type": "plain_text", "text": "View"}, "url": "https://example.com", "action_id": "view_link"},
                        {"type": "button", "text": {"type": "plain_text", "text": "Approve"}, "action_id": "approve", "value": "org/repo:42", "style": "primary"},
                    ]},
                    {"type": "context", "elements": [{"type": "mrkdwn", "text": "footer"}]},
                ],
            }],
        }

    def test_preserves_color(self):
        result = build_updated_attachments(self._make_message(), "Approved by <@U123>")
        assert result[0]["color"] == "#3498DB"

    def test_removes_action_buttons_keeps_view(self):
        result = build_updated_attachments(self._make_message(), "Approved by <@U123>")
        blocks = result[0]["blocks"]
        actions_block = [b for b in blocks if b["type"] == "actions"][0]
        assert len(actions_block["elements"]) == 1
        assert actions_block["elements"][0]["url"] == "https://example.com"

    def test_adds_action_context(self):
        result = build_updated_attachments(self._make_message(), "Approved by <@U123>")
        blocks = result[0]["blocks"]
        context_blocks = [b for b in blocks if b["type"] == "context"]
        texts = [c["elements"][0]["text"] for c in context_blocks]
        assert "Approved by <@U123>" in texts

    def test_preserves_non_action_blocks(self):
        result = build_updated_attachments(self._make_message(), "Done")
        blocks = result[0]["blocks"]
        section_blocks = [b for b in blocks if b["type"] == "section"]
        assert len(section_blocks) == 1
        assert "*title*" in section_blocks[0]["text"]["text"]

    def test_empty_attachments_returns_empty(self):
        result = build_updated_attachments({"attachments": []}, "Done")
        assert result == []

    def test_no_attachments_returns_empty(self):
        result = build_updated_attachments({}, "Done")
        assert result == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd slack-bot && .venv/bin/python -m pytest tests/test_utils.py -v`
Expected: FAIL with `ImportError: cannot import name 'parse_value'`

- [ ] **Step 3: Add parse_value, is_authorized, build_updated_attachments to bot.py**

Append to `slack-bot/bot.py`:

```python


def parse_value(value: str) -> tuple[str | None, int | None]:
    """Parse 'owner/repo:issue_number' from a button value."""
    parts = value.rsplit(":", 1)
    if len(parts) != 2:
        return None, None
    try:
        return parts[0], int(parts[1])
    except ValueError:
        return None, None


async def is_authorized(user_id: str, client) -> bool:
    """Check if a Slack user is authorized to use bot actions.

    Uses shared auth for user-level checks. Group membership is checked
    via the Slack API if ALLOWED_GROUP is configured.
    """
    if is_authorized_check(user_id, [], ALLOWED_USERS, ""):
        return True
    if ALLOWED_GROUP:
        try:
            result = await client.usergroups_users_list(usergroup=ALLOWED_GROUP)
            return user_id in result.get("users", [])
        except Exception:
            log.warning("Failed to check user group membership for %s", user_id)
    return False


def build_updated_attachments(message: dict, action_text: str) -> list[dict]:
    """Build updated attachments after a button action is taken.

    Replaces interactive buttons with a view-only link and appends
    a context block showing who performed the action.
    """
    attachments = message.get("attachments", [])
    if not attachments:
        return []
    old = attachments[0]
    blocks = old.get("blocks", [])
    color = old.get("color", "#95A5A6")

    updated: list[dict] = []
    for block in blocks:
        if block["type"] == "actions":
            view_url = None
            for elem in block.get("elements", []):
                if elem.get("url"):
                    view_url = elem["url"]
                    break
            if view_url:
                updated.append({
                    "type": "actions",
                    "elements": [{
                        "type": "button",
                        "text": {"type": "plain_text", "text": "View"},
                        "url": view_url,
                        "action_id": "view_link",
                    }],
                })
        else:
            updated.append(block)
    updated.append({
        "type": "context",
        "elements": [{"type": "mrkdwn", "text": action_text}],
    })
    return [{"color": color, "blocks": updated}]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd slack-bot && .venv/bin/python -m pytest tests/test_utils.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add slack-bot/bot.py slack-bot/tests/test_utils.py
git commit -m "feat(slack-bot): add parse_value, is_authorized, build_updated_attachments"
```

---

### Task 4: Button Handlers -- Approve and Retry (TDD)

**Files:**
- Create: `slack-bot/tests/test_interactions.py`
- Modify: `slack-bot/bot.py` (add `handle_approve`, `handle_retry`)

- [ ] **Step 1: Write test_interactions.py (button handler tests)**

```python
from unittest.mock import AsyncMock, patch

import pytest

from bot import handle_approve, handle_retry


def _make_body(action_id: str, value: str, user_id: str = "U123"):
    """Build a mock Slack action body for button clicks."""
    return {
        "user": {"id": user_id},
        "channel": {"id": "C456"},
        "actions": [{"action_id": action_id, "value": value}],
        "message": {
            "ts": "123.456",
            "text": "fallback",
            "attachments": [{
                "color": "#3498DB",
                "blocks": [
                    {"type": "section", "text": {"type": "mrkdwn", "text": "*title*"}},
                    {"type": "actions", "elements": [
                        {"type": "button", "text": {"type": "plain_text", "text": "View"}, "url": "https://example.com", "action_id": "view_link"},
                        {"type": "button", "text": {"type": "plain_text", "text": "Approve"}, "action_id": "approve", "value": value, "style": "primary"},
                    ]},
                    {"type": "context", "elements": [{"type": "mrkdwn", "text": "footer"}]},
                ],
            }],
        },
    }


class TestHandleApprove:
    @patch("bot.gh_dispatch", return_value=(True, ""))
    @patch("bot.gh_command", return_value=(True, ""))
    @pytest.mark.asyncio
    async def test_approve_adds_label(self, mock_gh, mock_dispatch):
        ack, client = AsyncMock(), AsyncMock()
        body = _make_body("approve", "org/repo:42")
        with patch("bot.ALLOWED_USERS", {"U123"}):
            await handle_approve(ack=ack, body=body, client=client)
        ack.assert_called_once()
        args = mock_gh.call_args[0][0]
        assert "agent:plan-approved" in args
        assert "--remove-label" in args

    @patch("bot.gh_dispatch", return_value=(True, ""))
    @patch("bot.gh_command", return_value=(True, ""))
    @pytest.mark.asyncio
    async def test_approve_uses_repo_from_value(self, mock_gh, mock_dispatch):
        ack, client = AsyncMock(), AsyncMock()
        body = _make_body("approve", "Frightful-Games/demo:42")
        with patch("bot.ALLOWED_USERS", {"U123"}):
            await handle_approve(ack=ack, body=body, client=client)
        args = mock_gh.call_args[0][0]
        assert "Frightful-Games/demo" in args

    @patch("bot.gh_dispatch", return_value=(True, ""))
    @patch("bot.gh_command", return_value=(True, ""))
    @pytest.mark.asyncio
    async def test_approve_updates_message(self, mock_gh, mock_dispatch):
        ack, client = AsyncMock(), AsyncMock()
        body = _make_body("approve", "org/repo:42")
        with patch("bot.ALLOWED_USERS", {"U123"}):
            await handle_approve(ack=ack, body=body, client=client)
        client.chat_update.assert_called_once()
        call_kwargs = client.chat_update.call_args.kwargs
        assert call_kwargs["ts"] == "123.456"
        assert call_kwargs["channel"] == "C456"

    @patch("bot.gh_dispatch", return_value=(True, ""))
    @patch("bot.gh_command", return_value=(True, ""))
    @pytest.mark.asyncio
    async def test_approve_sends_ephemeral_confirmation(self, mock_gh, mock_dispatch):
        ack, client = AsyncMock(), AsyncMock()
        body = _make_body("approve", "org/repo:42")
        with patch("bot.ALLOWED_USERS", {"U123"}):
            await handle_approve(ack=ack, body=body, client=client)
        client.chat_postEphemeral.assert_called()
        call_kwargs = client.chat_postEphemeral.call_args.kwargs
        assert "Done" in call_kwargs["text"]

    @patch("bot.gh_dispatch", return_value=(True, ""))
    @patch("bot.gh_command", return_value=(False, "gh auth login required"))
    @pytest.mark.asyncio
    async def test_approve_failure_reports_error(self, mock_gh, mock_dispatch):
        ack, client = AsyncMock(), AsyncMock()
        body = _make_body("approve", "org/repo:42")
        with patch("bot.ALLOWED_USERS", {"U123"}):
            await handle_approve(ack=ack, body=body, client=client)
        client.chat_postEphemeral.assert_called_once()
        assert "Failed" in client.chat_postEphemeral.call_args.kwargs["text"]
        client.chat_update.assert_not_called()

    @pytest.mark.asyncio
    async def test_unauthorized_user_rejected(self):
        ack, client = AsyncMock(), AsyncMock()
        body = _make_body("approve", "org/repo:42", user_id="U999")
        with patch("bot.ALLOWED_USERS", {"U123"}), patch("bot.ALLOWED_GROUP", ""):
            await handle_approve(ack=ack, body=body, client=client)
        client.chat_postEphemeral.assert_called_once()
        assert "permission" in client.chat_postEphemeral.call_args.kwargs["text"].lower()

    @patch("bot.gh_dispatch", return_value=(True, ""))
    @patch("bot.gh_command", return_value=(True, ""))
    @pytest.mark.asyncio
    async def test_approve_fires_dispatch(self, mock_gh, mock_dispatch):
        ack, client = AsyncMock(), AsyncMock()
        body = _make_body("approve", "org/repo:42")
        with patch("bot.ALLOWED_USERS", {"U123"}):
            await handle_approve(ack=ack, body=body, client=client)
        mock_dispatch.assert_called_once_with("org/repo", "agent-implement", 42)

    @patch("bot.gh_dispatch", return_value=(False, "dispatch failed"))
    @patch("bot.gh_command", return_value=(True, ""))
    @pytest.mark.asyncio
    async def test_dispatch_failure_warns_in_ephemeral(self, mock_gh, mock_dispatch):
        ack, client = AsyncMock(), AsyncMock()
        body = _make_body("approve", "org/repo:42")
        with patch("bot.ALLOWED_USERS", {"U123"}):
            await handle_approve(ack=ack, body=body, client=client)
        # Message should still update (label succeeded)
        client.chat_update.assert_called_once()
        # But ephemeral warns about dispatch
        text = client.chat_postEphemeral.call_args.kwargs["text"]
        assert "trigger" in text.lower() or "warning" in text.lower()


class TestHandleRetry:
    @patch("bot.gh_dispatch", return_value=(True, ""))
    @patch("bot.gh_command", return_value=(True, ""))
    @pytest.mark.asyncio
    async def test_retry_resets_labels(self, mock_gh, mock_dispatch):
        ack, client = AsyncMock(), AsyncMock()
        body = _make_body("retry", "org/repo:42")
        with patch("bot.ALLOWED_USERS", {"U123"}):
            await handle_retry(ack=ack, body=body, client=client)
        args = mock_gh.call_args[0][0]
        assert "--remove-label" in args
        assert "--add-label" in args
        assert "agent" in args

    @patch("bot.gh_dispatch", return_value=(True, ""))
    @patch("bot.gh_command", return_value=(True, ""))
    @pytest.mark.asyncio
    async def test_retry_fires_triage_dispatch(self, mock_gh, mock_dispatch):
        ack, client = AsyncMock(), AsyncMock()
        body = _make_body("retry", "org/repo:42")
        with patch("bot.ALLOWED_USERS", {"U123"}):
            await handle_retry(ack=ack, body=body, client=client)
        mock_dispatch.assert_called_once_with("org/repo", "agent-triage", 42)

    @pytest.mark.asyncio
    async def test_retry_unauthorized_rejected(self):
        ack, client = AsyncMock(), AsyncMock()
        body = _make_body("retry", "org/repo:42", user_id="U999")
        with patch("bot.ALLOWED_USERS", {"U123"}), patch("bot.ALLOWED_GROUP", ""):
            await handle_retry(ack=ack, body=body, client=client)
        client.chat_postEphemeral.assert_called_once()
        assert "permission" in client.chat_postEphemeral.call_args.kwargs["text"].lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd slack-bot && .venv/bin/python -m pytest tests/test_interactions.py -v`
Expected: FAIL with `ImportError: cannot import name 'handle_approve'`

- [ ] **Step 3: Add handle_approve and handle_retry to bot.py**

Append to `slack-bot/bot.py`:

```python


async def handle_approve(ack, body, client) -> None:
    """Handle Approve button click: add plan-approved label, trigger implementation."""
    await ack()
    user_id = body["user"]["id"]
    channel = body["channel"]["id"]

    if not await is_authorized(user_id, client):
        await client.chat_postEphemeral(channel=channel, user=user_id, text="You don't have permission to perform this action.")
        return

    repo, issue_number = parse_value(body["actions"][0]["value"])
    if repo is None:
        return

    ok, err = gh_command([
        "issue", "edit", str(issue_number), "--repo", repo,
        "--remove-label", "agent:plan-review", "--add-label", "agent:plan-approved",
    ])
    if not ok:
        await client.chat_postEphemeral(channel=channel, user=user_id, text=f"Failed to update GitHub issue #{issue_number}: {err}")
        return

    dispatch_ok, dispatch_err = gh_dispatch(repo, "agent-implement", issue_number)

    action_text = f"Approved by <@{user_id}>"
    attachments = build_updated_attachments(body["message"], action_text)
    await client.chat_update(channel=channel, ts=body["message"]["ts"], attachments=attachments, text=body["message"].get("text", ""))

    status = f"Done: Approved by <@{user_id}>"
    if not dispatch_ok:
        status += f" (warning: workflow trigger failed -- {dispatch_err})"
    await client.chat_postEphemeral(channel=channel, user=user_id, text=status)
    log.info("ACTION: approve on %s#%d by %s", repo, issue_number, user_id)


async def handle_retry(ack, body, client) -> None:
    """Handle Retry button click: reset labels, re-trigger triage."""
    await ack()
    user_id = body["user"]["id"]
    channel = body["channel"]["id"]

    if not await is_authorized(user_id, client):
        await client.chat_postEphemeral(channel=channel, user=user_id, text="You don't have permission to perform this action.")
        return

    repo, issue_number = parse_value(body["actions"][0]["value"])
    if repo is None:
        return

    ok, err = gh_command([
        "issue", "edit", str(issue_number), "--repo", repo,
        "--remove-label", ",".join(ALL_AGENT_LABELS), "--add-label", "agent",
    ])
    if not ok:
        await client.chat_postEphemeral(channel=channel, user=user_id, text=f"Failed to update GitHub issue #{issue_number}: {err}")
        return

    dispatch_ok, dispatch_err = gh_dispatch(repo, "agent-triage", issue_number)

    action_text = f"Retried by <@{user_id}>"
    attachments = build_updated_attachments(body["message"], action_text)
    await client.chat_update(channel=channel, ts=body["message"]["ts"], attachments=attachments, text=body["message"].get("text", ""))

    status = f"Done: Retried by <@{user_id}>"
    if not dispatch_ok:
        status += f" (warning: workflow trigger failed -- {dispatch_err})"
    await client.chat_postEphemeral(channel=channel, user=user_id, text=status)
    log.info("ACTION: retry on %s#%d by %s", repo, issue_number, user_id)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd slack-bot && .venv/bin/python -m pytest tests/test_interactions.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add slack-bot/bot.py slack-bot/tests/test_interactions.py
git commit -m "feat(slack-bot): add approve and retry button handlers"
```

---

### Task 5: Modal Flow -- Changes, Comment, Feedback Submit (TDD)

**Files:**
- Modify: `slack-bot/tests/test_interactions.py` (append modal tests)
- Modify: `slack-bot/bot.py` (add modal handlers)

- [ ] **Step 1: Append modal tests to test_interactions.py**

Add to bottom of `slack-bot/tests/test_interactions.py`:

```python
from bot import handle_changes, handle_comment, handle_feedback_submit, handle_view_link


class TestHandleChanges:
    @pytest.mark.asyncio
    async def test_opens_modal_with_trigger_id(self):
        ack, client = AsyncMock(), AsyncMock()
        body = _make_body("changes", "org/repo:42")
        body["trigger_id"] = "T123"
        with patch("bot.ALLOWED_USERS", {"U123"}):
            await handle_changes(ack=ack, body=body, client=client)
        ack.assert_called_once()
        client.views_open.assert_called_once()
        call_kwargs = client.views_open.call_args.kwargs
        assert call_kwargs["trigger_id"] == "T123"

    @pytest.mark.asyncio
    async def test_modal_has_feedback_input(self):
        ack, client = AsyncMock(), AsyncMock()
        body = _make_body("changes", "org/repo:42")
        body["trigger_id"] = "T123"
        with patch("bot.ALLOWED_USERS", {"U123"}):
            await handle_changes(ack=ack, body=body, client=client)
        view = client.views_open.call_args.kwargs["view"]
        assert view["type"] == "modal"
        assert view["callback_id"] == "feedback_modal"
        assert view["blocks"][0]["block_id"] == "feedback_block"

    @pytest.mark.asyncio
    async def test_modal_metadata_includes_repo_and_issue(self):
        ack, client = AsyncMock(), AsyncMock()
        body = _make_body("changes", "org/repo:42")
        body["trigger_id"] = "T123"
        with patch("bot.ALLOWED_USERS", {"U123"}):
            await handle_changes(ack=ack, body=body, client=client)
        view = client.views_open.call_args.kwargs["view"]
        import json
        meta = json.loads(view["private_metadata"])
        assert meta["action"] == "changes"
        assert meta["repo"] == "org/repo"
        assert meta["issue_number"] == 42

    @pytest.mark.asyncio
    async def test_unauthorized_user_rejected(self):
        ack, client = AsyncMock(), AsyncMock()
        body = _make_body("changes", "org/repo:42", user_id="U999")
        with patch("bot.ALLOWED_USERS", {"U123"}), patch("bot.ALLOWED_GROUP", ""):
            await handle_changes(ack=ack, body=body, client=client)
        client.views_open.assert_not_called()


class TestHandleComment:
    @pytest.mark.asyncio
    async def test_opens_modal_with_comment_action(self):
        ack, client = AsyncMock(), AsyncMock()
        body = _make_body("comment", "org/repo:42")
        body["trigger_id"] = "T123"
        with patch("bot.ALLOWED_USERS", {"U123"}):
            await handle_comment(ack=ack, body=body, client=client)
        view = client.views_open.call_args.kwargs["view"]
        import json
        meta = json.loads(view["private_metadata"])
        assert meta["action"] == "comment"


class TestHandleViewLink:
    @pytest.mark.asyncio
    async def test_acks_without_error(self):
        ack = AsyncMock()
        await handle_view_link(ack=ack)
        ack.assert_called_once()


class TestHandleFeedbackSubmit:
    def _make_view_body(self, action="changes", feedback_text="Please add more tests to the PR"):
        import json
        return {
            "user": {"id": "U123"},
        }, {
            "private_metadata": json.dumps({
                "action": action,
                "repo": "org/repo",
                "issue_number": 42,
                "channel": "C456",
                "ts": "123.456",
            }),
            "state": {
                "values": {
                    "feedback_block": {
                        "feedback_input": {"value": feedback_text},
                    },
                },
            },
        }

    @patch("bot.gh_dispatch", return_value=(True, ""))
    @patch("bot.gh_command", return_value=(True, ""))
    @pytest.mark.asyncio
    async def test_posts_comment_to_github(self, mock_gh, mock_dispatch):
        ack, client = AsyncMock(), AsyncMock()
        body, view = self._make_view_body()
        with patch("bot.ALLOWED_USERS", {"U123"}):
            await handle_feedback_submit(ack=ack, body=body, client=client, view=view)
        mock_gh.assert_called_once()
        args = mock_gh.call_args[0][0]
        assert "issue" in args
        assert "comment" in args
        assert "org/repo" in args

    @patch("bot.gh_dispatch", return_value=(True, ""))
    @patch("bot.gh_command", return_value=(True, ""))
    @pytest.mark.asyncio
    async def test_posts_thread_reply(self, mock_gh, mock_dispatch):
        ack, client = AsyncMock(), AsyncMock()
        body, view = self._make_view_body()
        with patch("bot.ALLOWED_USERS", {"U123"}):
            await handle_feedback_submit(ack=ack, body=body, client=client, view=view)
        client.chat_postMessage.assert_called_once()
        call_kwargs = client.chat_postMessage.call_args.kwargs
        assert call_kwargs["thread_ts"] == "123.456"
        assert call_kwargs["channel"] == "C456"

    @patch("bot.gh_dispatch", return_value=(True, ""))
    @patch("bot.gh_command", return_value=(True, ""))
    @pytest.mark.asyncio
    async def test_fires_reply_dispatch(self, mock_gh, mock_dispatch):
        ack, client = AsyncMock(), AsyncMock()
        body, view = self._make_view_body()
        with patch("bot.ALLOWED_USERS", {"U123"}):
            await handle_feedback_submit(ack=ack, body=body, client=client, view=view)
        mock_dispatch.assert_called_once_with("org/repo", "agent-reply", 42)

    @patch("bot.gh_dispatch", return_value=(True, ""))
    @patch("bot.gh_command", return_value=(False, "API error"))
    @pytest.mark.asyncio
    async def test_gh_failure_posts_ephemeral_error(self, mock_gh, mock_dispatch):
        ack, client = AsyncMock(), AsyncMock()
        body, view = self._make_view_body()
        with patch("bot.ALLOWED_USERS", {"U123"}):
            await handle_feedback_submit(ack=ack, body=body, client=client, view=view)
        client.chat_postEphemeral.assert_called_once()
        assert "Failed" in client.chat_postEphemeral.call_args.kwargs["text"]
        client.chat_postMessage.assert_not_called()

    @patch("bot.gh_dispatch", return_value=(True, ""))
    @patch("bot.gh_command", return_value=(True, ""))
    @pytest.mark.asyncio
    async def test_changes_action_label(self, mock_gh, mock_dispatch):
        ack, client = AsyncMock(), AsyncMock()
        body, view = self._make_view_body(action="changes")
        with patch("bot.ALLOWED_USERS", {"U123"}):
            await handle_feedback_submit(ack=ack, body=body, client=client, view=view)
        text = client.chat_postMessage.call_args.kwargs["text"]
        assert "Changes requested" in text

    @patch("bot.gh_dispatch", return_value=(True, ""))
    @patch("bot.gh_command", return_value=(True, ""))
    @pytest.mark.asyncio
    async def test_comment_action_label(self, mock_gh, mock_dispatch):
        ack, client = AsyncMock(), AsyncMock()
        body, view = self._make_view_body(action="comment")
        with patch("bot.ALLOWED_USERS", {"U123"}):
            await handle_feedback_submit(ack=ack, body=body, client=client, view=view)
        text = client.chat_postMessage.call_args.kwargs["text"]
        assert "Comment posted" in text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd slack-bot && .venv/bin/python -m pytest tests/test_interactions.py -v -k "Changes or Comment or Feedback or ViewLink"`
Expected: FAIL with `ImportError`

- [ ] **Step 3: Add modal handlers to bot.py**

Append to `slack-bot/bot.py`:

```python


async def _open_feedback_modal(
    client, trigger_id: str, action: str, repo: str,
    issue_number: int, channel: str, ts: str,
) -> None:
    """Open a Slack modal for free-text feedback."""
    title = f"Changes #{issue_number}" if action == "changes" else f"Comment #{issue_number}"
    placeholder = "Describe the changes you'd like..." if action == "changes" else "Enter your comment..."

    metadata = json.dumps({
        "action": action, "repo": repo, "issue_number": issue_number,
        "channel": channel, "ts": ts,
    })
    await client.views_open(
        trigger_id=trigger_id,
        view={
            "type": "modal",
            "callback_id": "feedback_modal",
            "private_metadata": metadata,
            "title": {"type": "plain_text", "text": title[:24]},
            "submit": {"type": "plain_text", "text": "Submit"},
            "blocks": [{
                "type": "input",
                "block_id": "feedback_block",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "feedback_input",
                    "multiline": True,
                    "min_length": 10,
                    "max_length": 2000,
                    "placeholder": {"type": "plain_text", "text": placeholder},
                },
                "label": {"type": "plain_text", "text": "Feedback"},
            }],
        },
    )


async def handle_changes(ack, body, client) -> None:
    """Handle Request Changes button: open feedback modal."""
    await ack()
    user_id = body["user"]["id"]
    if not await is_authorized(user_id, client):
        await client.chat_postEphemeral(channel=body["channel"]["id"], user=user_id, text="You don't have permission to perform this action.")
        return

    repo, issue_number = parse_value(body["actions"][0]["value"])
    if repo is None:
        return

    await _open_feedback_modal(
        client, body["trigger_id"], "changes", repo, issue_number,
        body["channel"]["id"], body["message"]["ts"],
    )


async def handle_comment(ack, body, client) -> None:
    """Handle Comment button: open feedback modal."""
    await ack()
    user_id = body["user"]["id"]
    if not await is_authorized(user_id, client):
        await client.chat_postEphemeral(channel=body["channel"]["id"], user=user_id, text="You don't have permission to perform this action.")
        return

    repo, issue_number = parse_value(body["actions"][0]["value"])
    if repo is None:
        return

    await _open_feedback_modal(
        client, body["trigger_id"], "comment", repo, issue_number,
        body["channel"]["id"], body["message"]["ts"],
    )


async def handle_view_link(ack) -> None:
    """No-op handler for View link buttons (Slack requires ack)."""
    await ack()


async def handle_feedback_submit(ack, body, client, view) -> None:
    """Handle feedback modal submission: post comment to GitHub, reply in thread."""
    await ack()
    meta = json.loads(view["private_metadata"])
    action = meta["action"]
    repo = meta["repo"]
    issue_number = meta["issue_number"]
    channel = meta["channel"]
    ts = meta["ts"]
    user_id = body["user"]["id"]

    feedback = sanitize_input(
        view["state"]["values"]["feedback_block"]["feedback_input"]["value"]
    )

    ok, err = gh_command(["issue", "comment", str(issue_number), "--repo", repo, "--body", feedback])
    if not ok:
        await client.chat_postEphemeral(channel=channel, user=user_id, text=f"Failed to comment on #{issue_number}: {err}")
        return

    action_label = "Changes requested" if action == "changes" else "Comment posted"
    await client.chat_postMessage(
        channel=channel, thread_ts=ts,
        text=f"{action_label} by <@{user_id}>",
    )

    gh_dispatch(repo, "agent-reply", issue_number)
    log.info("MODAL: %s on %s#%d by %s", action, repo, issue_number, user_id)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd slack-bot && .venv/bin/python -m pytest tests/test_interactions.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add slack-bot/bot.py slack-bot/tests/test_interactions.py
git commit -m "feat(slack-bot): add modal flow for changes and comments"
```

---

### Task 6: Slash Commands (TDD)

**Files:**
- Create: `slack-bot/tests/test_commands.py`
- Modify: `slack-bot/bot.py` (add 5 slash command handlers)

- [ ] **Step 1: Write test_commands.py**

```python
import json
from unittest.mock import AsyncMock, patch

import pytest

from bot import cmd_approve, cmd_reject, cmd_comment, cmd_status, cmd_retry


def _cmd_body(text: str, user_id: str = "U123"):
    """Build a mock slash command body."""
    return {
        "user_id": user_id,
        "channel_id": "C456",
        "text": text,
    }


class TestCmdApprove:
    @patch("bot.gh_dispatch", return_value=(True, ""))
    @patch("bot.gh_command", return_value=(True, ""))
    @pytest.mark.asyncio
    async def test_approves_issue(self, mock_gh, mock_dispatch):
        ack, respond, client = AsyncMock(), AsyncMock(), AsyncMock()
        with patch("bot.ALLOWED_USERS", {"U123"}), patch("bot.DEFAULT_REPO", "org/repo"):
            await cmd_approve(ack=ack, respond=respond, body=_cmd_body("42"), client=client)
        ack.assert_called_once()
        args = mock_gh.call_args[0][0]
        assert "agent:plan-approved" in args
        mock_dispatch.assert_called_once_with("org/repo", "agent-implement", 42)
        respond.assert_called_once()
        assert "Approved" in respond.call_args.kwargs["text"]

    @pytest.mark.asyncio
    async def test_rejects_missing_issue_number(self):
        ack, respond, client = AsyncMock(), AsyncMock(), AsyncMock()
        with patch("bot.ALLOWED_USERS", {"U123"}):
            await cmd_approve(ack=ack, respond=respond, body=_cmd_body(""), client=client)
        assert "Usage" in respond.call_args.kwargs["text"]

    @pytest.mark.asyncio
    async def test_rejects_non_numeric_issue(self):
        ack, respond, client = AsyncMock(), AsyncMock(), AsyncMock()
        with patch("bot.ALLOWED_USERS", {"U123"}):
            await cmd_approve(ack=ack, respond=respond, body=_cmd_body("abc"), client=client)
        assert "Usage" in respond.call_args.kwargs["text"]

    @pytest.mark.asyncio
    async def test_unauthorized(self):
        ack, respond, client = AsyncMock(), AsyncMock(), AsyncMock()
        with patch("bot.ALLOWED_USERS", {"U123"}), patch("bot.ALLOWED_GROUP", ""):
            await cmd_approve(ack=ack, respond=respond, body=_cmd_body("42", user_id="U999"), client=client)
        assert "permission" in respond.call_args.kwargs["text"].lower()


class TestCmdReject:
    @patch("bot.gh_dispatch", return_value=(True, ""))
    @patch("bot.gh_command", return_value=(True, ""))
    @pytest.mark.asyncio
    async def test_rejects_with_reason(self, mock_gh, mock_dispatch):
        ack, respond, client = AsyncMock(), AsyncMock(), AsyncMock()
        with patch("bot.ALLOWED_USERS", {"U123"}), patch("bot.DEFAULT_REPO", "org/repo"):
            await cmd_reject(ack=ack, respond=respond, body=_cmd_body("42 needs more tests"), client=client)
        # First gh_command call is the comment
        comment_args = mock_gh.call_args_list[0][0][0]
        assert "comment" in comment_args
        assert "needs more tests" in " ".join(comment_args)
        mock_dispatch.assert_called_once_with("org/repo", "agent-reply", 42)

    @patch("bot.gh_dispatch", return_value=(True, ""))
    @patch("bot.gh_command", return_value=(True, ""))
    @pytest.mark.asyncio
    async def test_rejects_with_default_reason(self, mock_gh, mock_dispatch):
        ack, respond, client = AsyncMock(), AsyncMock(), AsyncMock()
        with patch("bot.ALLOWED_USERS", {"U123"}), patch("bot.DEFAULT_REPO", "org/repo"):
            await cmd_reject(ack=ack, respond=respond, body=_cmd_body("42"), client=client)
        comment_args = mock_gh.call_args_list[0][0][0]
        assert "Rejected via Slack" in " ".join(comment_args)

    @pytest.mark.asyncio
    async def test_rejects_missing_issue(self):
        ack, respond, client = AsyncMock(), AsyncMock(), AsyncMock()
        with patch("bot.ALLOWED_USERS", {"U123"}):
            await cmd_reject(ack=ack, respond=respond, body=_cmd_body(""), client=client)
        assert "Usage" in respond.call_args.kwargs["text"]


class TestCmdComment:
    @patch("bot.gh_dispatch", return_value=(True, ""))
    @patch("bot.gh_command", return_value=(True, ""))
    @pytest.mark.asyncio
    async def test_posts_comment(self, mock_gh, mock_dispatch):
        ack, respond, client = AsyncMock(), AsyncMock(), AsyncMock()
        with patch("bot.ALLOWED_USERS", {"U123"}), patch("bot.DEFAULT_REPO", "org/repo"):
            await cmd_comment(ack=ack, respond=respond, body=_cmd_body("42 looks good"), client=client)
        comment_args = mock_gh.call_args[0][0]
        assert "comment" in comment_args
        assert "looks good" in " ".join(comment_args)
        mock_dispatch.assert_called_once_with("org/repo", "agent-reply", 42)

    @pytest.mark.asyncio
    async def test_requires_text(self):
        ack, respond, client = AsyncMock(), AsyncMock(), AsyncMock()
        with patch("bot.ALLOWED_USERS", {"U123"}):
            await cmd_comment(ack=ack, respond=respond, body=_cmd_body("42"), client=client)
        assert "Usage" in respond.call_args.kwargs["text"]


class TestCmdStatus:
    @patch("bot.gh_command")
    @pytest.mark.asyncio
    async def test_shows_agent_labels(self, mock_gh):
        mock_gh.return_value = (True, json.dumps({
            "title": "Fix bug",
            "state": "OPEN",
            "labels": [{"name": "agent:in-progress"}, {"name": "bug"}],
        }))
        ack, respond, client = AsyncMock(), AsyncMock(), AsyncMock()
        with patch("bot.ALLOWED_USERS", {"U123"}), patch("bot.DEFAULT_REPO", "org/repo"):
            await cmd_status(ack=ack, respond=respond, body=_cmd_body("42"), client=client)
        text = respond.call_args.kwargs["text"]
        assert "agent:in-progress" in text
        assert "Fix bug" in text

    @patch("bot.gh_command")
    @pytest.mark.asyncio
    async def test_no_agent_labels(self, mock_gh):
        mock_gh.return_value = (True, json.dumps({
            "title": "Doc update",
            "state": "OPEN",
            "labels": [{"name": "docs"}],
        }))
        ack, respond, client = AsyncMock(), AsyncMock(), AsyncMock()
        with patch("bot.ALLOWED_USERS", {"U123"}), patch("bot.DEFAULT_REPO", "org/repo"):
            await cmd_status(ack=ack, respond=respond, body=_cmd_body("42"), client=client)
        text = respond.call_args.kwargs["text"]
        assert "No agent labels" in text


class TestCmdRetry:
    @patch("bot.gh_dispatch", return_value=(True, ""))
    @patch("bot.gh_command", return_value=(True, ""))
    @pytest.mark.asyncio
    async def test_retries_issue(self, mock_gh, mock_dispatch):
        ack, respond, client = AsyncMock(), AsyncMock(), AsyncMock()
        with patch("bot.ALLOWED_USERS", {"U123"}), patch("bot.DEFAULT_REPO", "org/repo"):
            await cmd_retry(ack=ack, respond=respond, body=_cmd_body("42"), client=client)
        args = mock_gh.call_args[0][0]
        assert "--remove-label" in args
        assert "--add-label" in args
        mock_dispatch.assert_called_once_with("org/repo", "agent-triage", 42)

    @pytest.mark.asyncio
    async def test_rejects_missing_issue(self):
        ack, respond, client = AsyncMock(), AsyncMock(), AsyncMock()
        with patch("bot.ALLOWED_USERS", {"U123"}):
            await cmd_retry(ack=ack, respond=respond, body=_cmd_body(""), client=client)
        assert "Usage" in respond.call_args.kwargs["text"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd slack-bot && .venv/bin/python -m pytest tests/test_commands.py -v`
Expected: FAIL with `ImportError`

- [ ] **Step 3: Add slash command handlers to bot.py**

Append to `slack-bot/bot.py`:

```python


async def cmd_approve(ack, respond, body, client) -> None:
    """/agent-approve <issue_number> -- approve a plan."""
    await ack()
    user_id = body["user_id"]
    if not await is_authorized(user_id, client):
        await respond(text="You don't have permission to perform this action.")
        return

    text = body.get("text", "").strip()
    if not text or not text.isdigit():
        await respond(text="Usage: /agent-approve <issue_number>")
        return

    issue_number = int(text)
    repo = DEFAULT_REPO

    ok, err = gh_command([
        "issue", "edit", str(issue_number), "--repo", repo,
        "--remove-label", "agent:plan-review", "--add-label", "agent:plan-approved",
    ])
    if not ok:
        await respond(text=f"Failed to approve #{issue_number}: {err}")
        return

    gh_dispatch(repo, "agent-implement", issue_number)
    await respond(text=f"Approved #{issue_number} and triggered implementation.")
    log.info("CMD: approve %s#%d by %s", repo, issue_number, user_id)


async def cmd_reject(ack, respond, body, client) -> None:
    """/agent-reject <issue_number> [reason] -- reject with optional reason."""
    await ack()
    user_id = body["user_id"]
    if not await is_authorized(user_id, client):
        await respond(text="You don't have permission to perform this action.")
        return

    text = body.get("text", "").strip()
    parts = text.split(maxsplit=1)
    if not parts or not parts[0].isdigit():
        await respond(text="Usage: /agent-reject <issue_number> [reason]")
        return

    issue_number = int(parts[0])
    reason = sanitize_input(parts[1]) if len(parts) > 1 else "Rejected via Slack"
    repo = DEFAULT_REPO

    ok, err = gh_command(["issue", "comment", str(issue_number), "--repo", repo, "--body", reason])
    if not ok:
        await respond(text=f"Failed to reject #{issue_number}: {err}")
        return

    gh_command([
        "issue", "edit", str(issue_number), "--repo", repo,
        "--remove-label", "agent:plan-review", "--add-label", "agent:needs-info",
    ])
    gh_dispatch(repo, "agent-reply", issue_number)
    await respond(text=f"Rejected #{issue_number}: {reason[:100]}")
    log.info("CMD: reject %s#%d by %s", repo, issue_number, user_id)


async def cmd_comment(ack, respond, body, client) -> None:
    """/agent-comment <issue_number> <text> -- post feedback."""
    await ack()
    user_id = body["user_id"]
    if not await is_authorized(user_id, client):
        await respond(text="You don't have permission to perform this action.")
        return

    text = body.get("text", "").strip()
    parts = text.split(maxsplit=1)
    if len(parts) < 2 or not parts[0].isdigit():
        await respond(text="Usage: /agent-comment <issue_number> <text>")
        return

    issue_number = int(parts[0])
    comment_text = sanitize_input(parts[1])
    repo = DEFAULT_REPO

    ok, err = gh_command(["issue", "comment", str(issue_number), "--repo", repo, "--body", comment_text])
    if not ok:
        await respond(text=f"Failed to comment on #{issue_number}: {err}")
        return

    gh_dispatch(repo, "agent-reply", issue_number)
    await respond(text=f"Comment posted on #{issue_number}.")
    log.info("CMD: comment %s#%d by %s", repo, issue_number, user_id)


async def cmd_status(ack, respond, body, client) -> None:
    """/agent-status <issue_number> -- check current agent labels."""
    await ack()
    user_id = body["user_id"]
    if not await is_authorized(user_id, client):
        await respond(text="You don't have permission to perform this action.")
        return

    text = body.get("text", "").strip()
    if not text or not text.isdigit():
        await respond(text="Usage: /agent-status <issue_number>")
        return

    issue_number = int(text)
    repo = DEFAULT_REPO

    ok, output = gh_command(["issue", "view", str(issue_number), "--repo", repo, "--json", "labels,title,state"])
    if not ok:
        await respond(text=f"Failed to get status for #{issue_number}: {output}")
        return

    data = json.loads(output)
    title = data.get("title", "Unknown")
    state = data.get("state", "unknown")
    labels = [l["name"] for l in data.get("labels", []) if l["name"].startswith("agent")]
    status = ", ".join(labels) if labels else "No agent labels"

    await respond(text=f"*#{issue_number}: {title}*\nState: {state}\nAgent labels: {status}")
    log.info("CMD: status %s#%d by %s", repo, issue_number, user_id)


async def cmd_retry(ack, respond, body, client) -> None:
    """/agent-retry <issue_number> -- re-trigger agent."""
    await ack()
    user_id = body["user_id"]
    if not await is_authorized(user_id, client):
        await respond(text="You don't have permission to perform this action.")
        return

    text = body.get("text", "").strip()
    if not text or not text.isdigit():
        await respond(text="Usage: /agent-retry <issue_number>")
        return

    issue_number = int(text)
    repo = DEFAULT_REPO

    ok, err = gh_command([
        "issue", "edit", str(issue_number), "--repo", repo,
        "--remove-label", ",".join(ALL_AGENT_LABELS), "--add-label", "agent",
    ])
    if not ok:
        await respond(text=f"Failed to retry #{issue_number}: {err}")
        return

    gh_dispatch(repo, "agent-triage", issue_number)
    await respond(text=f"Retried #{issue_number} -- agent will re-triage.")
    log.info("CMD: retry %s#%d by %s", repo, issue_number, user_id)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd slack-bot && .venv/bin/python -m pytest tests/test_commands.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add slack-bot/bot.py slack-bot/tests/test_commands.py
git commit -m "feat(slack-bot): add slash commands"
```

---

### Task 7: Notification HTTP Handler (TDD)

**Files:**
- Create: `slack-bot/tests/test_http.py`
- Modify: `slack-bot/bot.py` (add `create_notify_handler`)

- [ ] **Step 1: Write test_http.py**

```python
from unittest.mock import AsyncMock, patch

import pytest

from bot import create_notify_handler


VALID_PAYLOAD = {
    "event_type": "plan_posted",
    "title": "Add caching",
    "url": "https://github.com/org/repo/issues/42",
    "description": "Plan summary here",
    "issue_number": 42,
    "repo": "org/repo",
}


@pytest.fixture
def mock_client():
    client = AsyncMock()
    client.chat_postMessage = AsyncMock(return_value={"ok": True})
    return client


@pytest.fixture
def handler(mock_client):
    with patch("bot.CHANNEL_ID", "C789"):
        return create_notify_handler(mock_client)


@pytest.fixture
def make_request():
    def _make(data: dict):
        request = AsyncMock()
        request.json = AsyncMock(return_value=data)
        return request
    return _make


class TestNotifyHandler:
    @pytest.mark.asyncio
    async def test_sends_message_to_channel(self, handler, mock_client, make_request):
        request = make_request(VALID_PAYLOAD)
        response = await handler(request)
        assert response.status == 200
        mock_client.chat_postMessage.assert_called_once()

    @pytest.mark.asyncio
    async def test_message_includes_blocks_in_attachment(self, handler, mock_client, make_request):
        request = make_request(VALID_PAYLOAD)
        await handler(request)
        call_kwargs = mock_client.chat_postMessage.call_args.kwargs
        assert "attachments" in call_kwargs
        attachment = call_kwargs["attachments"][0]
        assert "blocks" in attachment
        assert "color" in attachment

    @pytest.mark.asyncio
    async def test_attachment_color_matches_event(self, handler, mock_client, make_request):
        request = make_request(VALID_PAYLOAD)
        await handler(request)
        call_kwargs = mock_client.chat_postMessage.call_args.kwargs
        assert call_kwargs["attachments"][0]["color"] == "#3498DB"

    @pytest.mark.asyncio
    async def test_blocks_include_action_buttons(self, handler, mock_client, make_request):
        request = make_request(VALID_PAYLOAD)
        await handler(request)
        call_kwargs = mock_client.chat_postMessage.call_args.kwargs
        blocks = call_kwargs["attachments"][0]["blocks"]
        action_blocks = [b for b in blocks if b["type"] == "actions"]
        assert len(action_blocks) == 1
        action_ids = [e.get("action_id") for e in action_blocks[0]["elements"]]
        assert "approve" in action_ids

    @pytest.mark.asyncio
    async def test_fallback_text_includes_title(self, handler, mock_client, make_request):
        request = make_request(VALID_PAYLOAD)
        await handler(request)
        call_kwargs = mock_client.chat_postMessage.call_args.kwargs
        assert "Add caching" in call_kwargs["text"]

    @pytest.mark.asyncio
    async def test_sends_to_configured_channel(self, mock_client, make_request):
        with patch("bot.CHANNEL_ID", "C999"):
            handler = create_notify_handler(mock_client)
        request = make_request(VALID_PAYLOAD)
        await handler(request)
        assert mock_client.chat_postMessage.call_args.kwargs["channel"] == "C999"

    @pytest.mark.asyncio
    async def test_returns_503_when_channel_not_configured(self, mock_client, make_request):
        with patch("bot.CHANNEL_ID", ""):
            handler = create_notify_handler(mock_client)
        request = make_request(VALID_PAYLOAD)
        response = await handler(request)
        assert response.status == 503

    @pytest.mark.asyncio
    async def test_handles_missing_optional_fields(self, handler, mock_client, make_request):
        minimal = {"event_type": "tests_passed", "title": "T", "url": "https://x.com", "issue_number": 1, "repo": "r"}
        request = make_request(minimal)
        response = await handler(request)
        assert response.status == 200
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd slack-bot && .venv/bin/python -m pytest tests/test_http.py -v`
Expected: FAIL with `ImportError: cannot import name 'create_notify_handler'`

- [ ] **Step 3: Add create_notify_handler to bot.py**

Append to `slack-bot/bot.py`:

```python


def create_notify_handler(slack_client):
    """Create an aiohttp handler that sends notifications to Slack."""

    async def handle_notify(request: web.Request) -> web.Response:
        if not CHANNEL_ID:
            return web.Response(status=503, text="Channel not configured")

        data = await request.json()
        event_type = data["event_type"]
        title = data["title"]
        url = data["url"]
        description = data.get("description", "")
        issue_number = data.get("issue_number", 0)
        repo = data.get("repo", "")

        blocks = build_blocks(event_type, title, url, description, issue_number, repo)
        actions = build_actions(event_type, issue_number, url, repo)
        color = EVENT_COLORS.get(event_type, "#95A5A6")

        indicator = EVENT_INDICATORS.get(event_type, "[INFO]")
        label = EVENT_LABELS.get(event_type, "Agent Update")
        fallback_text = f"{indicator} {label} -- #{issue_number}: {title}"

        await slack_client.chat_postMessage(
            channel=CHANNEL_ID,
            text=fallback_text,
            attachments=[{"color": color, "blocks": blocks + actions}],
        )
        return web.Response(text="OK")

    return handle_notify
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd slack-bot && .venv/bin/python -m pytest tests/test_http.py -v`
Expected: All tests PASS

- [ ] **Step 5: Run all tests to verify nothing is broken**

Run: `cd slack-bot && .venv/bin/python -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add slack-bot/bot.py slack-bot/tests/test_http.py
git commit -m "feat(slack-bot): add notification HTTP handler"
```

---

### Task 8: App Wiring and Entrypoint

**Files:**
- Modify: `slack-bot/bot.py` (add `create_app`, `run`, `main`)

- [ ] **Step 1: Add create_app, run, and main to bot.py**

Append to `slack-bot/bot.py`:

```python


def create_app():
    """Create and configure the Slack AsyncApp with all handlers."""
    from slack_bolt.async_app import AsyncApp as _AsyncApp

    slack_app = _AsyncApp(token=BOT_TOKEN)
    slack_app.action("approve")(handle_approve)
    slack_app.action("retry")(handle_retry)
    slack_app.action("changes")(handle_changes)
    slack_app.action("comment")(handle_comment)
    slack_app.action("view_link")(handle_view_link)
    slack_app.view("feedback_modal")(handle_feedback_submit)
    slack_app.command("/agent-approve")(cmd_approve)
    slack_app.command("/agent-reject")(cmd_reject)
    slack_app.command("/agent-comment")(cmd_comment)
    slack_app.command("/agent-status")(cmd_status)
    slack_app.command("/agent-retry")(cmd_retry)
    return slack_app


async def run() -> None:
    """Start HTTP listener and Socket Mode handler."""
    from slack_bolt.adapter.socket_mode.aiohttp import AsyncSocketModeHandler

    app = create_app()
    handler = create_notify_handler(app.client)
    http_runner = await start_http_server(handler, port=BOT_PORT)

    try:
        socket_handler = AsyncSocketModeHandler(app, APP_TOKEN)
        await socket_handler.start_async()
    finally:
        await http_runner.cleanup()


def main() -> None:
    """Bot entrypoint."""
    import asyncio

    if not BOT_TOKEN:
        print("Error: AGENT_SLACK_BOT_TOKEN is not set")
        raise SystemExit(1)
    if not APP_TOKEN:
        print("Error: AGENT_SLACK_APP_TOKEN is not set")
        raise SystemExit(1)
    if not CHANNEL_ID:
        print("Error: AGENT_SLACK_CHANNEL_ID is not set")
        raise SystemExit(1)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    asyncio.run(run())


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify the module loads without errors**

Run: `cd slack-bot && .venv/bin/python -c "from bot import create_app, run, main; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Run all tests**

Run: `cd slack-bot && .venv/bin/python -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add slack-bot/bot.py
git commit -m "feat(slack-bot): add app wiring and entrypoint"
```

---

### Task 9: Deployment Files

**Files:**
- Create: `slack-bot/agent-dispatch-slack.service`
- Create: `slack-bot/install.sh`
- Create: `slack-bot/CLAUDE.md`
- Create: `slack-bot/README.md`

- [ ] **Step 1: Create agent-dispatch-slack.service**

```ini
[Unit]
Description=Agent Dispatch Slack Bot
StartLimitIntervalSec=300
StartLimitBurst=5

[Service]
Type=simple
WorkingDirectory=WORKING_DIR
EnvironmentFile=CONFIG_PATH
ExecStart=WORKING_DIR/.venv/bin/python bot.py
Restart=on-failure
RestartSec=10
TimeoutStopSec=30

[Install]
WantedBy=default.target
```

- [ ] **Step 2: Create install.sh**

```bash
#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="agent-dispatch-slack"

echo "=== Agent Dispatch Slack Bot Install ==="

# Determine config.env path (same logic as agent-dispatch.sh)
DEFAULT_CONFIG="${AGENT_CONFIG:-${HOME}/agent-infra/config.env}"
read -r -p "Path to config.env [${DEFAULT_CONFIG}]: " CONFIG_PATH
CONFIG_PATH="${CONFIG_PATH:-$DEFAULT_CONFIG}"

if [ ! -f "$CONFIG_PATH" ]; then
    echo "Warning: ${CONFIG_PATH} not found. Create it before starting the bot."
fi

# Create venv if it doesn't exist or is broken
if [ -d "${SCRIPT_DIR}/.venv" ] && [ ! -f "${SCRIPT_DIR}/.venv/bin/pip" ]; then
    echo "Removing broken virtual environment..."
    rm -rf "${SCRIPT_DIR}/.venv"
fi
if [ ! -d "${SCRIPT_DIR}/.venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv "${SCRIPT_DIR}/.venv"
fi

echo "Installing dependencies..."
"${SCRIPT_DIR}/.venv/bin/pip" install -q -r "${SCRIPT_DIR}/requirements.txt"

# Install systemd service
echo "Installing systemd service..."
SERVICE_FILE="${HOME}/.config/systemd/user/${SERVICE_NAME}.service"
mkdir -p "$(dirname "$SERVICE_FILE")"

sed "s|WORKING_DIR|${SCRIPT_DIR}|g; s|CONFIG_PATH|${CONFIG_PATH}|g" \
    "${SCRIPT_DIR}/agent-dispatch-slack.service" > "$SERVICE_FILE"

systemctl --user daemon-reload
systemctl --user disable "$SERVICE_NAME" 2>/dev/null || true
systemctl --user enable "$SERVICE_NAME"

echo ""
echo "Install complete. To start the bot:"
echo "  systemctl --user start ${SERVICE_NAME}"
echo ""
echo "To check status:"
echo "  systemctl --user status ${SERVICE_NAME}"
echo "  journalctl --user -u ${SERVICE_NAME} -f"
echo ""
echo "Make sure these are set in your config.env (${CONFIG_PATH}):"
echo "  AGENT_SLACK_BOT_TOKEN       (xoxb-... Bot User OAuth Token)"
echo "  AGENT_SLACK_APP_TOKEN       (xapp-... App-Level Token for Socket Mode)"
echo "  AGENT_SLACK_CHANNEL_ID      (Channel ID for notifications)"
echo "  AGENT_SLACK_ALLOWED_USERS   (Comma-separated Slack user IDs)"
echo "  AGENT_DISPATCH_REPO         (owner/repo format)"
echo ""
echo "For the bot to start at boot (without requiring login):"
echo "  sudo loginctl enable-linger $(whoami)"
```

- [ ] **Step 3: Run shellcheck on install.sh**

Run: `shellcheck slack-bot/install.sh`
Expected: No errors

- [ ] **Step 4: Create CLAUDE.md**

```markdown
# Slack Bot

Interactive Slack bot for agent dispatch notifications and control. This is a standalone Python application that runs as a systemd service alongside the dispatch scripts.

## Architecture

`bot.py` runs two services: a Slack bot (slack-bolt, Socket Mode) and a local HTTP API (aiohttp on port 8676). The dispatch scripts send notifications to the HTTP API, and the bot formats and sends them to Slack as Block Kit messages with interactive buttons.

## Key Flows

- **Dispatch -> Bot**: `scripts/lib/notify.sh` POSTs to `http://127.0.0.1:8676/notify`
- **Bot -> GitHub**: Button clicks and slash commands call `gh` CLI to add labels or post comments
- **Fallback**: If the bot is unreachable, `notify.sh` falls back to webhook mode

## Development

- Python 3.10+, dependencies in `requirements.txt`
- Tests in `tests/` (pytest, pytest-asyncio)
- Authorization via `AGENT_SLACK_ALLOWED_USERS` and `AGENT_SLACK_ALLOWED_GROUP`
- Input sanitization removes shell-dangerous characters (caps at 2000 chars)
- Handler functions are standalone async functions registered with the app in `create_app()`
- Tests call handlers directly with mock `ack`/`body`/`client` args (no app needed)
```

- [ ] **Step 5: Create README.md**

Create `slack-bot/README.md` with the full setup guide. Follow the structure of `discord-bot/README.md` but adapted for Slack:

```markdown
# Agent Dispatch Slack Bot

Interactive Slack bot for managing agent work. Adds buttons, slash commands, and modals on top of the webhook notification layer.

## Prerequisites

- Python 3.10+ with `python3-venv` package
- `gh` CLI authenticated with repo access
- A Slack workspace you have admin access to

## Step-by-Step Setup

### 1. Create the Slack App

1. Go to [Slack API Apps](https://api.slack.com/apps)
2. Click **"Create New App"** > **"From scratch"**
3. Name it (e.g., "Agent Dispatch") and select your workspace

### 2. Enable Socket Mode

1. In the left sidebar, click **"Socket Mode"**
2. Toggle **Enable Socket Mode** to on
3. Create an **App-Level Token** with the `connections:write` scope
4. Name it (e.g., "socket-mode") and click **Generate**
5. **Copy the `xapp-` token immediately**

### 3. Configure Bot Token Scopes

1. In the left sidebar, click **"OAuth & Permissions"**
2. Under **Bot Token Scopes**, add:
   - `chat:write` -- send and update messages
   - `commands` -- slash commands
3. If using `AGENT_SLACK_ALLOWED_GROUP`, also add:
   - `usergroups:read` -- check user group membership

### 4. Create Slash Commands

1. In the left sidebar, click **"Slash Commands"**
2. Create each command:

| Command | Description |
|---|---|
| `/agent-approve` | Approve an agent plan |
| `/agent-reject` | Reject a plan with optional reason |
| `/agent-comment` | Post feedback on an issue |
| `/agent-status` | Check current agent labels |
| `/agent-retry` | Re-trigger the agent |

For each: click **"Create New Command"**, enter the command name and a short description, set the Request URL to anything (Socket Mode ignores it, but the field is required -- use `https://localhost`).

### 5. Enable Interactivity

1. In the left sidebar, click **"Interactivity & Shortcuts"**
2. Toggle **Interactivity** to on
3. Set the Request URL to `https://localhost` (Socket Mode handles routing)

### 6. Install to Workspace

1. In the left sidebar, click **"Install App"**
2. Click **"Install to Workspace"** and authorize
3. **Copy the `xoxb-` Bot User OAuth Token**

### 7. Get Your Slack IDs

| ID | How to get it |
|---|---|
| **Channel ID** | Right-click channel name > View channel details > scroll to bottom |
| **Your User ID** | Click your profile picture > Profile > three dots menu > Copy member ID |

### 8. Configure

```bash
mkdir -p ~/agent-infra
nano ~/agent-infra/config.env
```

Add:

```bash
AGENT_SLACK_BOT_TOKEN="xoxb-your-bot-token"
AGENT_SLACK_APP_TOKEN="xapp-your-app-token"
AGENT_SLACK_CHANNEL_ID="C0123456789"
AGENT_SLACK_ALLOWED_USERS="U0123456789"  # comma-separated for multiple
AGENT_DISPATCH_REPO="owner/repo"
```

### 9. Install and Start

```bash
cd slack-bot
./install.sh
```

When prompted, enter the path to your config (e.g., `/home/youruser/agent-infra/config.env`).

Then start:

```bash
systemctl --user start agent-dispatch-slack
```

### 10. Verify

Check the service status:

```bash
systemctl --user status agent-dispatch-slack
```

Send a test notification:

```bash
curl -X POST http://127.0.0.1:8676/notify \
  -H "Content-Type: application/json" \
  -d '{"event_type":"plan_posted","title":"Test notification","url":"https://github.com","description":"Testing the bot","issue_number":0,"repo":"test/repo"}'
```

You should see a notification with buttons in your Slack channel.

## Managing the Bot

```bash
# Start
systemctl --user start agent-dispatch-slack

# Stop
systemctl --user stop agent-dispatch-slack

# Restart (after config changes)
systemctl --user restart agent-dispatch-slack

# View logs
journalctl --user -u agent-dispatch-slack -f

# Disable auto-start
systemctl --user disable agent-dispatch-slack
```

## Buttons

| Button | Action |
|---|---|
| View | Link to GitHub issue/PR |
| Approve | Adds `agent:plan-approved` label, triggers implementation |
| Request Changes | Opens modal, posts comment, triggers re-triage |
| Comment | Opens modal, posts comment |
| Retry | Resets labels, adds `agent` to re-trigger |

## Slash Commands

| Command | Description |
|---|---|
| `/agent-approve <issue>` | Approve a plan |
| `/agent-reject <issue> [reason]` | Reject with optional reason |
| `/agent-comment <issue> <text>` | Post feedback |
| `/agent-status <issue>` | Check current agent labels |
| `/agent-retry <issue>` | Re-trigger agent |

## Troubleshooting

### Bot connects but no notifications appear

- Check that `AGENT_SLACK_CHANNEL_ID` is set correctly
- Verify the bot is invited to the channel (if private)
- Check the HTTP listener: `curl -s http://127.0.0.1:8676/notify` should not return "connection refused"

### Buttons don't respond

- Verify your Slack User ID is in `AGENT_SLACK_ALLOWED_USERS`
- Check the bot logs: `journalctl --user -u agent-dispatch-slack -f`
- Ensure **Interactivity** is enabled in the Slack app settings

### Slash commands not found

- Verify the commands are created in the Slack app settings
- Ensure Socket Mode is enabled
- Try reinstalling the app to your workspace

## Privacy

This bot processes Slack button clicks, modal submissions, and slash commands to manage GitHub issues. No user data is collected or stored beyond operational logs.
```

- [ ] **Step 6: Commit**

```bash
git add slack-bot/agent-dispatch-slack.service slack-bot/install.sh slack-bot/CLAUDE.md slack-bot/README.md
git commit -m "feat(slack-bot): add deployment files and documentation"
```

---

## Design Notes

**Modal message updates**: Button actions (approve, retry) update the original Slack message inline because the interaction payload includes `body["message"]`. Modal submissions (changes, comment) post a thread reply instead, because Slack's view submission payload does not carry the original message reference. Adding inline updates for modals would require `channels:history`/`groups:history` scopes and a `conversations.history` API call -- a reasonable future enhancement.

**Async architecture**: `AsyncSocketModeHandler.start_async()` runs on the asyncio event loop alongside the aiohttp HTTP server started by `start_http_server()`. Both services share the same loop, started by `asyncio.run()` in `main()`.

**Testing strategy**: All handler functions are standalone async functions that accept `ack`, `body`, `client`, etc. as arguments. Tests call them directly with `AsyncMock` objects, without needing to create a Slack app or connect to Socket Mode. This matches the pattern used by the Discord bot tests.

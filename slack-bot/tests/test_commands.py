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

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

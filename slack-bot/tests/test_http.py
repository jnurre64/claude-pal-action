import logging
from unittest.mock import AsyncMock, patch

import pytest

import bot as bot_module
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
def handler(mock_client, monkeypatch):
    # Default CHANNEL_ID so tests that don't exercise routing get a channel.
    monkeypatch.setattr(bot_module, "CHANNEL_ID", "C789")
    monkeypatch.setattr(bot_module, "CHANNEL_MAP", {})
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
    async def test_sends_to_configured_channel(self, mock_client, make_request, monkeypatch):
        monkeypatch.setattr(bot_module, "CHANNEL_ID", "C999")
        monkeypatch.setattr(bot_module, "CHANNEL_MAP", {})
        handler = create_notify_handler(mock_client)
        request = make_request(VALID_PAYLOAD)
        await handler(request)
        assert mock_client.chat_postMessage.call_args.kwargs["channel"] == "C999"

    @pytest.mark.asyncio
    async def test_returns_200_when_repo_unmapped_and_no_default(self, mock_client, make_request, monkeypatch):
        # Per-repo routing: no mapping + no default = silent drop (200), not error.
        monkeypatch.setattr(bot_module, "CHANNEL_ID", "")
        monkeypatch.setattr(bot_module, "CHANNEL_MAP", {})
        handler = create_notify_handler(mock_client)
        request = make_request(VALID_PAYLOAD)
        response = await handler(request)
        assert response.status == 200
        mock_client.chat_postMessage.assert_not_called()

    @pytest.mark.asyncio
    async def test_handles_missing_optional_fields(self, handler, mock_client, make_request):
        minimal = {"event_type": "tests_passed", "title": "T", "url": "https://x.com", "issue_number": 1, "repo": "r"}
        request = make_request(minimal)
        response = await handler(request)
        assert response.status == 200


class TestPerRepoChannelRouting:
    @pytest.mark.asyncio
    async def test_routes_to_mapped_channel_when_repo_matches(
        self, monkeypatch, mock_client, make_request
    ):
        monkeypatch.setattr(bot_module, "CHANNEL_MAP", {"org/repo": "CABC999"})
        monkeypatch.setattr(bot_module, "CHANNEL_ID", "C111")
        handler = create_notify_handler(mock_client)
        await handler(make_request(VALID_PAYLOAD))
        assert mock_client.chat_postMessage.call_args.kwargs["channel"] == "CABC999"

    @pytest.mark.asyncio
    async def test_falls_back_to_default_when_repo_not_in_map(
        self, monkeypatch, mock_client, make_request
    ):
        monkeypatch.setattr(bot_module, "CHANNEL_MAP", {"other/repo": "CABC999"})
        monkeypatch.setattr(bot_module, "CHANNEL_ID", "C111")
        handler = create_notify_handler(mock_client)
        await handler(make_request(VALID_PAYLOAD))
        assert mock_client.chat_postMessage.call_args.kwargs["channel"] == "C111"

    @pytest.mark.asyncio
    async def test_returns_200_when_repo_explicitly_muted(
        self, monkeypatch, mock_client, make_request
    ):
        monkeypatch.setattr(bot_module, "CHANNEL_MAP", {"org/repo": ""})
        monkeypatch.setattr(bot_module, "CHANNEL_ID", "C111")
        handler = create_notify_handler(mock_client)
        response = await handler(make_request(VALID_PAYLOAD))
        assert response.status == 200
        mock_client.chat_postMessage.assert_not_called()

    @pytest.mark.asyncio
    async def test_multiple_repos_route_to_different_channels(
        self, monkeypatch, mock_client, make_request
    ):
        monkeypatch.setattr(
            bot_module,
            "CHANNEL_MAP",
            {"org/repo-a": "CA111", "org/repo-b": "CB222"},
        )
        monkeypatch.setattr(bot_module, "CHANNEL_ID", "")
        handler = create_notify_handler(mock_client)
        await handler(make_request({**VALID_PAYLOAD, "repo": "org/repo-a"}))
        await handler(make_request({**VALID_PAYLOAD, "repo": "org/repo-b"}))
        channels = [c.kwargs["channel"] for c in mock_client.chat_postMessage.call_args_list]
        assert "CA111" in channels
        assert "CB222" in channels

    @pytest.mark.asyncio
    async def test_info_log_emitted_with_match_direct(
        self, monkeypatch, mock_client, make_request, caplog
    ):
        monkeypatch.setattr(bot_module, "CHANNEL_MAP", {"org/repo": "CABC999"})
        monkeypatch.setattr(bot_module, "CHANNEL_ID", "C111")
        handler = create_notify_handler(mock_client)
        with caplog.at_level(logging.INFO, logger="dispatch-bot"):
            await handler(make_request(VALID_PAYLOAD))
        assert any("match=direct" in r.message for r in caplog.records)

    @pytest.mark.asyncio
    async def test_info_log_emitted_with_match_fallback(
        self, monkeypatch, mock_client, make_request, caplog
    ):
        monkeypatch.setattr(bot_module, "CHANNEL_MAP", {"other/repo": "CABC999"})
        monkeypatch.setattr(bot_module, "CHANNEL_ID", "C111")
        handler = create_notify_handler(mock_client)
        with caplog.at_level(logging.INFO, logger="dispatch-bot"):
            await handler(make_request(VALID_PAYLOAD))
        assert any("match=fallback" in r.message for r in caplog.records)

    @pytest.mark.asyncio
    async def test_info_log_emitted_with_match_muted(
        self, monkeypatch, mock_client, make_request, caplog
    ):
        monkeypatch.setattr(bot_module, "CHANNEL_MAP", {"org/repo": ""})
        monkeypatch.setattr(bot_module, "CHANNEL_ID", "C111")
        handler = create_notify_handler(mock_client)
        with caplog.at_level(logging.INFO, logger="dispatch-bot"):
            await handler(make_request(VALID_PAYLOAD))
        assert any("match=muted" in r.message for r in caplog.records)

    @pytest.mark.asyncio
    async def test_info_log_emitted_with_match_dropped(
        self, monkeypatch, mock_client, make_request, caplog
    ):
        monkeypatch.setattr(bot_module, "CHANNEL_MAP", {"other/repo": "CABC999"})
        monkeypatch.setattr(bot_module, "CHANNEL_ID", "")
        handler = create_notify_handler(mock_client)
        with caplog.at_level(logging.INFO, logger="dispatch-bot"):
            await handler(make_request(VALID_PAYLOAD))
        assert any("match=dropped" in r.message for r in caplog.records)

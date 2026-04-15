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

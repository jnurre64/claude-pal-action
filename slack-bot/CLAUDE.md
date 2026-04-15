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

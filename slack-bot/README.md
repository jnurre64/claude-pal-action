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

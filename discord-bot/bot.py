"""Discord bot for claude-agent-dispatch interactive notifications."""

import logging
import os
import re
import subprocess

import discord
from discord.ext import commands
from aiohttp import web

log = logging.getLogger("dispatch-bot")

# --- Configuration (from environment) ---
BOT_TOKEN = os.environ.get("AGENT_DISCORD_BOT_TOKEN", "")
CHANNEL_ID = int(os.environ.get("AGENT_DISCORD_CHANNEL_ID", "0"))
GUILD_ID = int(os.environ.get("AGENT_DISCORD_GUILD_ID", "0"))
ALLOWED_USERS = set(os.environ.get("AGENT_DISCORD_ALLOWED_USERS", "").split(",")) - {""}
ALLOWED_ROLE = os.environ.get("AGENT_DISCORD_ALLOWED_ROLE", "")
BOT_PORT = int(os.environ.get("AGENT_DISCORD_BOT_PORT", "8675"))


def sanitize_input(text: str) -> str:
    """Remove shell-dangerous characters from user input."""
    return re.sub(r"[`$\\]", "", text)[:2000]


def parse_custom_id(custom_id: str) -> tuple[str | None, str | None, int | None]:
    """Parse 'action:owner/repo:issue_number' from a button custom_id.

    Returns (action, repo, issue_number) or (None, None, None) on failure.
    """
    parts = custom_id.split(":")
    if len(parts) < 3:
        return None, None, None
    action = parts[0]
    num_str = parts[-1]
    repo = ":".join(parts[1:-1])
    try:
        return action, repo, int(num_str)
    except ValueError:
        return None, None, None


def is_authorized_check(
    user_id: str, role_ids: list[str], allowed_users: set[str], allowed_role: str
) -> bool:
    """Check if a user is authorized to perform bot actions."""
    if not allowed_users and not allowed_role:
        return False
    if user_id in allowed_users:
        return True
    if allowed_role and allowed_role in role_ids:
        return True
    return False


# --- Event metadata ---
EVENT_COLORS = {
    "pr_created": 0x57F287, "tests_passed": 0x57F287, "review_pushed": 0x57F287,
    "tests_failed": 0xED4245, "agent_failed": 0xED4245,
    "plan_posted": 0x3498DB, "questions_asked": 0x3498DB,
    "review_feedback": 0xFFFF00,
}

EVENT_LABELS = {
    "plan_posted": "Plan Ready", "questions_asked": "Questions",
    "implement_started": "Implementation Started",
    "tests_passed": "Tests Passed", "tests_failed": "Tests Failed",
    "pr_created": "PR Created", "review_feedback": "Review Feedback",
    "review_pushed": "Review Fixes Pushed",
    "agent_failed": "Agent Failed",
}

EVENT_INDICATORS = {
    "pr_created": "[OK]", "tests_passed": "[OK]", "review_pushed": "[OK]",
    "tests_failed": "[FAIL]", "agent_failed": "[FAIL]",
    "plan_posted": "[INFO]", "questions_asked": "[INFO]",
    "review_feedback": "[ACTION]", "implement_started": "[INFO]",
}

# Events that get action buttons (not just a View link)
_PLAN_EVENTS = {"plan_posted"}
_RETRY_EVENTS = {"agent_failed"}


def build_embed(
    event_type: str, title: str, url: str, description: str, issue_number: int, repo: str
) -> discord.Embed:
    """Build a Discord embed for a dispatch notification."""
    indicator = EVENT_INDICATORS.get(event_type, "[INFO]")
    label = EVENT_LABELS.get(event_type, "Agent Update")
    color = EVENT_COLORS.get(event_type, 0x95A5A6)

    embed = discord.Embed(
        title=f"{indicator} {label} -- #{issue_number}: {title}",
        url=url,
        description=description[:4000],
        color=color,
    )
    embed.set_footer(text=f"Automated by claude-agent-dispatch | {repo} #{issue_number}")
    return embed


def build_buttons(event_type: str, issue_number: int, url: str, repo: str) -> discord.ui.View:
    """Build interactive buttons for a notification message."""
    view = discord.ui.View(timeout=None)
    view.add_item(discord.ui.Button(label="View", url=url, style=discord.ButtonStyle.link))

    if event_type in _PLAN_EVENTS:
        view.add_item(discord.ui.Button(
            label="Approve", custom_id=f"approve:{repo}:{issue_number}", style=discord.ButtonStyle.success
        ))
        view.add_item(discord.ui.Button(
            label="Request Changes", custom_id=f"changes:{repo}:{issue_number}", style=discord.ButtonStyle.danger
        ))
        view.add_item(discord.ui.Button(
            label="Comment", custom_id=f"comment:{repo}:{issue_number}", style=discord.ButtonStyle.secondary
        ))
    elif event_type in _RETRY_EVENTS:
        view.add_item(discord.ui.Button(
            label="Retry", custom_id=f"retry:{repo}:{issue_number}", style=discord.ButtonStyle.primary
        ))

    return view


def gh_command(args: list[str]) -> tuple[bool, str]:
    """Execute a gh CLI command and return (success, output)."""
    try:
        result = subprocess.run(
            ["gh"] + args, capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            log.warning("gh %s failed: %s", " ".join(args[:3]), result.stderr.strip())
            return False, result.stderr.strip()
        return True, result.stdout.strip()
    except subprocess.TimeoutExpired:
        log.error("gh command timed out: %s", " ".join(args[:3]))
        return False, "Error: command timed out"


def gh_dispatch(repo: str, event_type: str, issue_number: int) -> tuple[bool, str]:
    """Fire a repository_dispatch event to trigger a workflow."""
    return gh_command([
        "api", f"repos/{repo}/dispatches",
        "-f", f"event_type={event_type}",
        "-f", f"client_payload[issue_number]={issue_number}",
    ])


_ALL_AGENT_LABELS = [
    "agent:failed", "agent:triage", "agent:needs-info", "agent:ready",
    "agent:in-progress", "agent:pr-open", "agent:plan-review", "agent:plan-approved",
    "agent:revision",
]


class FeedbackModal(discord.ui.Modal):
    """Modal dialog for collecting free-text feedback on an issue."""

    feedback = discord.ui.TextInput(
        label="Feedback",
        style=discord.TextStyle.paragraph,
        min_length=10,
        max_length=2000,
        placeholder="Describe the changes you'd like...",
    )

    def __init__(self, action: str, issue_number: int, repo: str):
        title = f"Request Changes on #{issue_number}" if action == "changes" else f"Comment on #{issue_number}"
        super().__init__(title=title[:45])
        self.action = action
        self.issue_number = issue_number
        self.repo = repo

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        text = sanitize_input(self.feedback.value)
        ok, err = gh_command(["issue", "comment", str(self.issue_number), "--repo", self.repo, "--body", text])
        if not ok:
            await interaction.followup.send(
                f"Failed to comment on #{self.issue_number}: {err}", ephemeral=True
            )
            return

        if interaction.message and interaction.message.embeds:
            action_label = "Changes requested" if self.action == "changes" else "Comment"
            embed = interaction.message.embeds[0]
            embed.add_field(
                name="Action", value=f"{action_label} by {interaction.user.display_name}", inline=False
            )
            await interaction.message.edit(embed=embed)

        gh_dispatch(self.repo, "agent-reply", self.issue_number)
        await interaction.followup.send("Feedback posted to GitHub.", ephemeral=True)
        log.info("MODAL: %s on %s#%d by %s (id=%s)", self.action, self.repo, self.issue_number, interaction.user, interaction.user.id)


async def handle_button_interaction(interaction: discord.Interaction) -> None:
    """Handle a button click on a notification message."""
    custom_id = interaction.data.get("custom_id", "")
    action, repo, issue_number = parse_custom_id(custom_id)
    if action is None or repo is None or issue_number is None:
        return

    user_id = str(interaction.user.id)
    role_ids = [str(r.id) for r in getattr(interaction.user, "roles", [])]

    if not is_authorized_check(user_id, role_ids, ALLOWED_USERS, ALLOWED_ROLE):
        await interaction.response.send_message(
            "You don't have permission to perform this action.", ephemeral=True
        )
        return

    if action in ("changes", "comment"):
        modal = FeedbackModal(action=action, issue_number=issue_number, repo=repo)
        await interaction.response.send_modal(modal)
        return

    await interaction.response.defer(ephemeral=True)

    if action == "approve":
        ok, err = gh_command([
            "issue", "edit", str(issue_number), "--repo", repo,
            "--remove-label", "agent:plan-review", "--add-label", "agent:plan-approved",
        ])
        status_text = f"Approved by {interaction.user.display_name}"
    elif action == "retry":
        ok, err = gh_command([
            "issue", "edit", str(issue_number), "--repo", repo,
            "--remove-label", ",".join(_ALL_AGENT_LABELS), "--add-label", "agent",
        ])
        status_text = f"Retried by {interaction.user.display_name}"
    else:
        await interaction.followup.send("Unknown action.", ephemeral=True)
        return

    if not ok:
        await interaction.followup.send(
            f"Failed to update GitHub issue #{issue_number}: {err}", ephemeral=True
        )
        return

    # Map button actions to dispatch event types
    dispatch_events = {"approve": "agent-implement", "retry": "agent-triage"}
    dispatch_ok, dispatch_err = gh_dispatch(repo, dispatch_events[action], issue_number)

    embed = interaction.message.embeds[0] if interaction.message.embeds else discord.Embed()
    embed.add_field(name="Action", value=status_text, inline=False)
    view = discord.ui.View(timeout=None)
    for row in interaction.message.components:
        for item in row.children:
            if hasattr(item, "url") and item.url:
                view.add_item(discord.ui.Button(label=item.label, url=item.url, style=discord.ButtonStyle.link))
    await interaction.message.edit(embed=embed, view=view)

    if not dispatch_ok:
        await interaction.followup.send(
            f"Done: {status_text} (warning: workflow trigger failed — {dispatch_err})",
            ephemeral=True,
        )
    else:
        await interaction.followup.send(f"Done: {status_text}", ephemeral=True)
    log.info("ACTION: %s on %s#%d by %s (id=%s)", action, repo, issue_number, interaction.user, interaction.user.id)


def create_notify_handler(bot):
    """Create an aiohttp handler that sends notifications via the bot's channel."""
    async def handle_notify(request: web.Request) -> web.Response:
        channel = bot.get_channel(CHANNEL_ID)
        if channel is None:
            return web.Response(status=503, text="Channel not found")

        data = await request.json()
        event_type = data["event_type"]
        title = data["title"]
        url = data["url"]
        description = data.get("description", "")
        issue_number = data.get("issue_number", 0)
        repo = data.get("repo", "")

        embed = build_embed(event_type, title, url, description, issue_number, repo)
        view = build_buttons(event_type, issue_number, url, repo)
        await channel.send(embed=embed, view=view)
        return web.Response(text="OK")

    return handle_notify


async def start_http_server(bot) -> web.AppRunner:
    """Start the local HTTP server for receiving dispatch notifications.

    Returns the AppRunner for cleanup on shutdown.
    """
    app = web.Application()
    handler = create_notify_handler(bot)
    app.router.add_post("/notify", handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", BOT_PORT)
    await site.start()
    log.info("HTTP listener on 127.0.0.1:%d", BOT_PORT)
    return runner


class DispatchBot(commands.Bot):
    """Discord bot with HTTP notification server."""

    def __init__(self) -> None:
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)
        self._http_runner: web.AppRunner | None = None

    async def setup_hook(self) -> None:
        """Start the HTTP server once, before the gateway connects."""
        self._http_runner = await start_http_server(self)

    async def on_ready(self) -> None:
        log.info("Bot ready: %s (guild %d)", self.user, GUILD_ID)
        channel = self.get_channel(CHANNEL_ID)
        if not channel:
            log.error("Channel %d not found — bot may not have access", CHANNEL_ID)

    async def on_interaction(self, interaction: discord.Interaction) -> None:
        if interaction.type == discord.InteractionType.component:
            await handle_button_interaction(interaction)

    async def close(self) -> None:
        if self._http_runner:
            await self._http_runner.cleanup()
        await super().close()


def main() -> None:
    """Bot entrypoint."""
    if not BOT_TOKEN:
        print("Error: AGENT_DISCORD_BOT_TOKEN is not set")
        raise SystemExit(1)
    if not CHANNEL_ID:
        print("Error: AGENT_DISCORD_CHANNEL_ID is not set")
        raise SystemExit(1)
    if not GUILD_ID:
        print("Error: AGENT_DISCORD_GUILD_ID is not set")
        raise SystemExit(1)

    bot = DispatchBot()
    bot.run(BOT_TOKEN, log_handler=logging.StreamHandler(), log_level=logging.INFO)


if __name__ == "__main__":
    main()

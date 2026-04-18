# Claude Code + Subscriptions + Local Automation: Summary Guide

## Terms of Service: The Clear Rules

**Explicitly allowed:**

- Running the official `claude` CLI binary on your own machine, authenticated with your Pro/Max/Team/Enterprise subscription
- Using `claude -p` (headless mode) for scripts, pipes, and local automation on your own computer
- Using `claude setup-token` to generate a long-lived OAuth token (`sk-ant-oat01-...`) for CI/CD environments where browser login isn't possible — this is Anthropic's officially documented path
- Anthropic's own GitHub Action (`anthropics/claude-code-action`) accepts `CLAUDE_CODE_OAUTH_TOKEN` as a supported input
- Docker's official sandbox integration for Claude Code with subscription auth
- Running Claude Code inside Docker containers on your own machine using the real CLI binary

**Explicitly prohibited (post-February 2026 policy):**

- Using subscription OAuth tokens in **any third-party tool, product, or service** — including the Agent SDK, OpenClaw, Cline, Cursor, OpenCode, and similar harnesses
- Extracting OAuth credentials from `~/.claude` to feed into non-Anthropic clients that make their own API calls
- Using the Agent SDK (Python/TypeScript) with subscription OAuth — API key required
- Offering Claude.ai login or proxying requests through Free/Pro/Max credentials for other end users
- Automated/non-human access to Claude Services except via API key or explicit permission (TOS Section 3.7)

## Areas of Genuine Concern

**The "ordinary individual usage" language.** The Feb 2026 policy added this phrase for Pro/Max plans. Sustained automation, parallel agents, or 24/7 background services on a subscription pushes outside this boundary — even when using the official CLI.

**The `ANTHROPIC_API_KEY` silent override.** If that env var is set anywhere in your shell or container, `claude -p` uses it without warning and bills to your Console API account. This has caused accidental charges in the thousands. Always verify with `/status`.

**Third-party tools that forward credentials.** Tools that copy/mount `~/.claude` into their own managed environments sit in a gray zone even when they invoke the real CLI inside. Mechanically often fine; culturally adjacent to banned patterns.

**Subscription quota mechanics.** Autonomous loops burn through Pro/Max weekly caps fast. A 50-iteration Ralph loop on a medium codebase can cost $50-100 in API-equivalent tokens. Pro is usually too tight for serious autonomous work; Max 20x gives real headroom.

**GitHub Actions gray zone.** Using `CLAUDE_CODE_OAUTH_TOKEN` in CI runners is documented by Anthropic, but high-volume automation pattern-matches to prohibited "service" usage. Fine for personal-scale CI; murky for team-wide or high-throughput deployments.

## Alternatives for Local Docker-Based Claude Code

Ranked by TOS safety and operational quality:

**1. Docker's Official Sandbox** — `sbx run claude --name my-sandbox -- "task"`

- Official Anthropic partner integration, documented subscription OAuth support
- Proxy handles OAuth flow so credentials aren't stored in sandbox
- microVM-based isolation, active maintenance, bug fixes tracking Anthropic auth changes
- Strongest institutional support

**2. Anthropic's Reference Devcontainer**

- Ships in Anthropic's Claude Code repo
- Built-in firewall with outbound allowlist
- Designed for `--dangerously-skip-permissions` autonomous operation
- `claude /login` inside container — no third-party credential layer
- Most policy-clean option

**3. Plain Docker + `CLAUDE_CODE_OAUTH_TOKEN`**

- Run `claude setup-token` on host, pass token to container via env var
- Exactly the use case Anthropic built `setup-token` for
- No third-party tool touches credentials — just the real CLI in a container
- Maximum control, minimum magic

**4. Claudebox / Claude-docker** (community, maintained)

- Pre-configured dev environments with profiles, MCP servers
- `claude-docker` includes Twilio notifications for long-running tasks
- Running the real CLI, no token impersonation
- Not officially blessed but not violating policy if configured correctly

**5. Claude-code-sandbox / Spritz** — **NOT RECOMMENDED**

- claude-code-sandbox archived since June 2025, predates Feb 2026 policy
- Credential forwarding model (copies `~/.claude.json` into containers) sits in murky territory
- Spritz successor is Kubernetes-oriented with OpenClaw as flagship example runtime
- Better alternatives exist without the risk profile

## Autonomous Loop Tools (Pair With Docker)

**Ralph Wiggum Plugin** (official Anthropic) — `/plugin install ralph-wiggum@claude-plugins-official`

- Canonical "work until done" pattern
- Stop hook re-feeds prompt until completion promise appears
- Inside your current Claude Code session, no external loops

**ralph-claude-code** (community, actively maintained)

- Production safeguards: exit detection, rate limiting, circuit breakers
- Handles 5-hour subscription window explicitly
- Task sources for GitHub issues, PRDs, beads

## Recommended Stack

For "plan an issue extensively, let Claude work continuously, local machine":

1. **Docker's official sandbox** for isolation (`sbx run claude`)
2. **Anthropic's Ralph Wiggum plugin** for the autonomous loop
3. **Write plans in a `PLAN.md`** checked into the repo
4. **Use tests as the verification signal** — completion promise triggers on test pass
5. **Max 20x subscription** if doing this regularly, or switch to API key billing for heavy automation

## Decision Framework

| Use case | Auth method | TOS posture |
|---|---|---|
| Personal scripts with `claude -p` on your machine | Subscription OAuth (`/login`) | Clearly allowed |
| Docker sandbox on your machine | Subscription OAuth via official integration | Clearly allowed |
| Personal GitHub Actions CI | `CLAUDE_CODE_OAUTH_TOKEN` from `setup-token` | Allowed, documented |
| Team CI / high-volume / 24-7 service | `ANTHROPIC_API_KEY` | Required under Commercial Terms |
| Any third-party agent tool (OpenClaw, Cline, etc.) | `ANTHROPIC_API_KEY` only | OAuth explicitly prohibited |
| Agent SDK usage | `ANTHROPIC_API_KEY` only | OAuth explicitly prohibited |

## The Bottom Line

Use the official `claude` CLI binary + your subscription for individual developer workflows, including Docker sandboxing. Use API keys for anything that smells like a service, runs unattended at scale, or involves non-Anthropic code making API calls. When in doubt, verify with `/status` that you're authenticating the way you think you are — the silent `ANTHROPIC_API_KEY` override is the most common footgun.

## Key References

- Claude Code Authentication Docs: <https://code.claude.com/docs/en/authentication>
- Claude Code Headless Docs: <https://code.claude.com/docs/en/headless>
- Pro/Max + Claude Code: <https://support.claude.com/en/articles/11145838-using-claude-code-with-your-pro-or-max-plan>
- Docker Sandboxes for Claude Code: <https://docs.docker.com/ai/sandboxes/agents/claude-code/>
- Anthropic's Ralph Wiggum Plugin: <https://github.com/anthropics/claude-code/tree/main/plugins/ralph-wiggum>
- Awesome Claude Code (community tools): <https://github.com/hesreallyhim/awesome-claude-code>

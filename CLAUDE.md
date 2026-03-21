# Claude Agent Dispatch

Reusable infrastructure for running Claude Code agents on GitHub issues via GitHub Actions.

## For New Users

Run `/setup` to configure this toolkit for your project.

## Architecture

- `scripts/agent-dispatch.sh` — Main dispatch entry point, sources `lib/` modules
- `scripts/lib/` — Modular functions: logging, labels, worktrees, data fetching, defaults
- `prompts/` — Default agent prompts (triage, implement, reply, review)
- `.github/workflows/dispatch-*.yml` — Reusable workflows called by consuming repos
- `config.env` — Project-specific configuration (not committed, see `config.env.example`)

## Development

- All shell scripts must pass `shellcheck` with zero warnings
- Run locally: `shellcheck scripts/*.sh scripts/lib/*.sh`
- CI runs ShellCheck on every push and PR to main
- Use `set -euo pipefail` in all scripts
- Keep functions focused — one purpose per function

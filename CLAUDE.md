# Claude Agent Dispatch

Reusable infrastructure for running Claude Code agents on GitHub issues via GitHub Actions.

## For New Users

Run `/setup` to configure this toolkit for your project.

## Architecture

- `scripts/agent-dispatch.sh` — Main dispatch entry point, sources `lib/` modules
- `scripts/lib/` — Modular functions: logging, labels, worktrees, data fetching, defaults
- `prompts/` — Default agent prompts (triage, implement, reply, review)
- `.github/workflows/dispatch-*.yml` — Reusable workflows called by consuming repos
- `config.defaults.env` — Project defaults, committed (see `config.defaults.env.example`)
- `config.env` — Sensitive overrides, gitignored (see `config.env.example`)

## Development

- All shell scripts must pass `shellcheck` with zero warnings
- Tests use BATS-Core (git submodules in `tests/`)
- Run checks: `shellcheck scripts/*.sh scripts/lib/*.sh && ./tests/bats/bin/bats tests/`
- CI runs both ShellCheck and BATS on every push and PR
- Use `set -euo pipefail` in all scripts
- Keep functions focused — one purpose per function
- Bug fix? Add a `REGRESSION vX.Y.Z:` test to prevent recurrence

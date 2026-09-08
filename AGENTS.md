# Working on sandbox-pal-action with Codex

This repository provides Bash orchestration, reusable GitHub Actions workflows,
and Python notification bots for agents working on GitHub issues.

## Project guidance

Read `CLAUDE.md` for the shared project overview and development conventions.
Keep it and `.claude/` working: Codex support is additive. Read the scoped
`AGENTS.md` before editing scripts, prompts, or either bot. Use the current code
and CI configuration to verify architectural details in older documentation.

Key references: `CONTRIBUTING.md`, `docs/architecture.md`,
`docs/configuration.md`, `docs/customization.md`, and `docs/security.md`.

## Development and validation

- Shell scripts use Bash, `set -euo pipefail`, and focused functions.
- Check prerequisites with `bash scripts/check-test-prereqs.sh`.
- For shell/runtime changes, run
  `shellcheck scripts/*.sh scripts/lib/*.sh` and
  `./tests/bats/bin/bats tests/`.
- Initialize missing test submodules with
  `git submodule update --init --recursive`.
- Add behavioral tests for features and `REGRESSION vX.Y.Z:` tests for bugs,
  following the existing test helpers and release version conventions.
- For bot changes, follow the relevant bot guidance and run its pytest suite.
- For documentation-only changes, check links, paths, and `git diff --check`;
  there is no need to run worker sessions.
- Do not edit vendored test submodules as part of routine project changes.

## Interactive client and worker engines

Codex can develop this repository and invoke the orchestrator shell interface.
Claude Code remains the default worker; Codex is selected with `AGENT_ENGINE`
or per-phase engine overrides. Changing `AGENT_MODEL` alone does not select a
different engine. See `docs/configuration.md` for native settings and capability
differences. Absolute instruction-file prevention is deferred hardening; preserve
the existing Claude workflow and all shared review/test gates.

`.agents/skills/` exposes the existing `sp-work`, `sp-status`, `sp-revise`, and
`sp-post-merge` orchestration skills through relative links to `.claude/skills/`.
Use `$sp-work`, `$sp-status`, `$sp-revise`, or `$sp-post-merge` in Codex;
slash-command references inside those shared files name the same skills.
Read a skill when the user requests its workflow. Ordinary repository
development and planning do not require dispatching the issue pipeline.

When dispatching, inspect semantic `outcome` as well as `exit_code`. A process
exit of zero can accompany `agent:failed`. Preserve the human plan approval,
fresh adversarial plan review, fresh post-implementation review, test gates,
locks, heartbeats, recovery branches, and bot anti-self-trigger behavior.

Keep credentials in the existing ignored configuration or runner secret store.
Do not commit personal Codex authentication or machine-specific settings.

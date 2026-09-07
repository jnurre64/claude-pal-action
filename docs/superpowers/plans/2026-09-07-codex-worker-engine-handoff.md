# Issue 116 implementation handoff

Prepared 2026-09-07. This file transfers the approved design and local work to a
fresh session. Continue from the committed milestones on the existing branch.

## Start here

1. Read root `AGENTS.md`, `CLAUDE.md`, and scoped guidance for files being edited.
2. Read the [implementation plan](2026-09-07-codex-worker-engine.md). It contains
   the code findings, proposed envelope, permission proof, migration sequence,
   test matrix, and source references.
3. Inspect `git status --short` and confirm branch `feat/116-codex-worker-engine`.
   Preserve all current changes. Do not reset, clean, or recreate this checkout.
4. Read issues [116](https://github.com/jnurre64/sandbox-pal-action/issues/116)
   and [112](https://github.com/jnurre64/sandbox-pal-action/issues/112) for any
   updates since planning, then continue from the implementation progress below.

Repository: `/home/jonny/repos/sandbox-pal-action`.
Remote: `git@github.com-infra:jnurre64/sandbox-pal-action.git`.
Planning base HEAD: `04cef68b433e90037b4f7af34b099e6005435a1c`.
The planning and implementation sessions made no pushes, PRs, issue comments,
or worker dispatches. The user subsequently authorized committing the validated
milestones for handoff; see the checkpoint below. These commits are local and
have not been pushed, so another clone needs them transferred first.

## Committed checkpoint — 2026-09-07

The previously uncommitted work is now captured in three milestone commits:

1. `f379d4e` — Codex repository guidance and shared skill discovery.
2. `7d076ea` — standalone asset delivery and recoverable updates (#112).
3. The commit containing this checkpoint, titled
   `feat: normalize Claude worker results and enforce phase outcomes (#116)` —
   neutral Claude adapter, schema dependency, consumer migration, tests and plans.

Use `git log -3 --oneline` to see the checkpoint commits. The historical progress
sections below describe the work before it was committed; references there to
uncommitted changes are historical. Preserve any new changes made afterward.
The next step remains engine/model resolution and reachable-phase preflight,
followed by Codex permission verification. No Codex worker support is claimed.

## Confirmed user decisions

- Implement the staged approach in the linked plan on a separate branch.
- Keep Claude supported and the default worker engine.
- Support both saved Codex login and API key authentication.
- Provide a dispatch-wide engine default plus optional per-phase engine overrides
  in the FIRST release. This supersedes the earlier single-engine-only suggestion.
- Users can configure both engines, e.g. Claude implements and Codex reviews.
- Preserve the human approval step and both independent fresh review sessions.
- Codex repository initialization is additive to the existing Claude setup.

Do not re-ask settled scope questions. Exact internal module names, envelope
field names, and engine-specific model-setting names in the plan are design
proposals, not already implemented public interfaces. Resolve routine details
from current code and compatibility requirements.

## Work already completed

- Root `AGENTS.md` explains project conventions, checks, client/worker separation,
  and semantic dispatch outcomes; it reads shared guidance from `CLAUDE.md`.
- Scoped guidance added in `scripts/AGENTS.md`, `prompts/AGENTS.md`,
  `discord-bot/AGENTS.md`, and `slack-bot/AGENTS.md`.
- Four relative directory symlinks expose existing orchestration skills:
  `.agents/skills/{sp-work,sp-status,sp-revise,sp-post-merge}` each points to
  `../../.claude/skills/<name>`. Their targets remain unchanged.
- `CONTRIBUTING.md` explains Codex and Claude development entry points.
- The implementation plan and this handoff are in `docs/superpowers/plans/`.

Existing `CLAUDE.md`, `.claude/`, workflows and production configuration are unchanged. Installer changes are
recorded in the continuation sections below, including the neutral Claude adapter.

Planning-session validation completed: `git diff --check`, root guidance path checks, all five
instruction files and their Claude counterparts exist, four skill links resolve
inside this repository, and existing Claude/runtime files have no diff.
No ShellCheck/BATS/pytest or live worker tests were run for these documentation
and discovery changes. Do not report the runtime suite as passing.

## Implementation progress — 2026-09-07 continuation

The #112 install/schema delivery changes are now local on the same branch:

- `scripts/lib/install-assets.sh` is the shared setup/update inventory for scripts,
  prompts, schemas, packaged `skills/`, setup workflow templates, and labels.
- Setup copies all inventoried assets and records upstream checksums. Update
  includes missing schemas even when the tracked revision already matches HEAD.
- `update.sh --yes` accepts safe updates/new assets while retaining customizations
  and skipping config edits. EOF conservatively defers remaining choices and
  completes bookkeeping for applied changes.
- Tracking retains previous baselines for customized/deferred files, records
  `pending_assets`, and is replaced atomically. Asset copies also use atomic
  replacement, including when the installed updater replaces itself. Rerunning
  recognizes a completed copy whose tracking write was interrupted.
- Workflow template changes emit a notice to reconcile actual `.github/workflows/`
  callers. Setup still renders callers there. Automated caller migration and
  interactive client instruction/skill destinations remain in milestone 5;
  this change does not expose checkout-relative skill symlinks to consumers.
- `docs/operations.md` and `CHANGELOG.md` describe the delivery/update behavior.

Validation: prerequisites, ShellCheck, `git diff --check`, and the final full
BATS suite pass (446 tests, including 46 installer tests). The full-suite log is
`/tmp/codex-worker-bats-final.log` in this session environment. BATS reports an
existing BW01 warning in `tests/test_defaults.bats:13` for the expected failing config load;
that test passes. No worker sessions or GitHub mutations have been performed.

The following continuation completes the neutral Claude adapter milestone.
Codex worker support remains unimplemented and unverified. Preserve all current
uncommitted changes, including the original repository initialization files.

## Implementation progress — neutral Claude adapter continuation

Issues #116 and #112 were re-read; neither had new comments. The branch remains
`feat/116-codex-worker-engine`; no commits, pushes, issue comments, PRs, paid
workers, or production changes were made.

- `scripts/lib/agent.sh` provides `run_agent`, semantic classification and failure
  reporting. `common.sh` sources it and keeps compatibility wrappers for old
  `run_claude`/parser callers. Every production dispatch and review phase now uses
  the neutral API. Strict shell options are scoped to worker subprocesses so
  sourcing `common.sh` does not change the caller's options.
- `scripts/lib/engine-claude.sh` retains Claude command construction, memory,
  models, tools, timeout, MCP, persistence, budgets, effort and permission flags.
- `scripts/lib/agent-result.py` produces exactly one version-1 envelope. Child
  exit status and semantic status are separate; malformed/multiple objects and
  partial failed structured output cannot create success. Auth, quota, rate
  limits, permission refusal, configuration, schema errors, caps, timeouts and
  observed child cancellation exit codes are distinguished. Unknown usage/cost
  is null and denial availability is explicit. Error kind `limit` represents
  Claude's turn/budget caps in addition to the proposed kinds in the plan.
- Schemas are checked before worker invocation, snapshotted for the CLI and
  harness, and validated against decoded/redacted structured output afterward.
  Missing/malformed schemas fail closed. Relative paths use `CONFIG_DIR`.
  Explicitly empty schema settings retain legacy parsing. Only in-document
  references and known drafts are accepted; `format` is an annotation.
- The dependency is `jsonschema>=4.18,<5`, delivered as
  `scripts/requirements-worker.txt` by the existing setup/update inventory.
  Prerequisite checks and CI include it; installation does not silently run pip.
- Capture logs have unique names per invocation. Decoded JSON credentials and
  stderr are scrubbed. This does not establish worker-proof capture isolation;
  the broader protected-path and process-tree proof remains in the Codex stage.
- All decision phases and review/retry sessions stop on semantic failure, even
  with process exit zero and valid-looking partial output. Test-fix auth/quota
  failures stop bounded recovery. Interrupted/capped implementation may recover
  only with both tests and independent post-implementation review enabled.
  Branch preservation, cleanup, public outcomes, and the human plan gate remain.
- `tests/test_agent.bats` adds 20 behavioral tests covering the envelope,
  telemetry, errors, schemas, redaction, inventory, every dispatch handler, both
  review gates and test-fix failure. Existing Claude argv tests remain. Review
  fixtures mock the engine beneath the real neutral runner.

Validation environment: system Python lacked `jsonschema`. An isolated temporary
venv at `/tmp/sandbox-pal-worker-venv` contains Python 3.12.3 and jsonschema 4.26.0.
Use `PATH="/tmp/sandbox-pal-worker-venv/bin:$PATH"` for prerequisite/BATS commands
in this checkout, or install the packaged requirements into another environment.
Do not assume that temporary venv will survive transfer to another machine.

Validation: prerequisites, ShellCheck and `git diff --check` pass. The full BATS
suite passes all 466 tests (`/tmp/neutral-bats-final.log`). A final focused run
of runner/redaction and common compatibility tests also passes all 116 tests
(`/tmp/neutral-redaction-final.log`). The existing BW01 warning remains at
`tests/test_defaults.bats:13` for its expected failing config load. No live
worker sessions were run; mocks do not establish Codex support.

Next implementation step: resolve and freeze engine/model/policy configuration,
including per-phase overrides and reachable-phase preflight; then perform the
Codex capability and permission proof before enabling its adapter. Worker
process-tree supervision, portable worker assets, and isolated live fixtures
remain pending. Webber and the operator's authentication were not changed.

## Implementation order

1. Fix #112 asset delivery in both setup and update. Establish an asset inventory
   covering schemas and other adapter dependencies, checksum bookkeeping,
   customization preservation, and fresh-install/upgrade tests. Investigate EOF
   handling so partially applied updates cannot leave misleading metadata.
2. Add a neutral runner/envelope with the Claude adapter first. Migrate every
   dispatch and review consumer, preserving current flags and behavior except
   explicitly documented schema/semantic-outcome correctness fixes.
3. Add engine and model resolution, including first-release phase overrides.
   Freeze the phase map at dispatch start and preflight every engine reachable
   for that event, including bounded fix/retry phases. Do not require an unused
   engine's credentials. Never pass an inherited Claude model to Codex.
4. Prove the Codex sandbox, approval, command, network, MCP, and protected-path
   policies, then implement the Codex adapter. Refuse unsupported controls; do
   not replace missing controls with unrestricted access.
5. Integrate portable memory/instructions/skills, installer destinations,
   workflows, credential handling and documentation. Keep Claude entry points.
6. Run complete local validation, then opt-in isolated all-Codex and mixed-engine
   pipeline fixtures. Record evidence before claiming worker support.

Use the implementation plan's detailed acceptance tests for each milestone.
Keep changes reviewable and capture material decisions and verification evidence
in the plan or a progress record as work proceeds.

## Critical technical constraints

- `scripts/lib/common.sh:run_claude` currently couples command construction,
  memory, schemas, output capture, and errors. Nonzero exits can append a second
  synthetic object after raw output. Normalize to exactly one result object.
- Success requires semantic success, not merely process exit zero. Existing
  orchestrator/last-dispatch `outcome` is public behavior. `agent:failed` with
  `exit_code:0` must not trigger advancement or false success reporting.
- Keep auth/quota/configuration failures distinct from bounded retryable errors.
  Missing usage/cost/denial telemetry is unknown, not zero. Do not promise a
  Codex dollar or turn cap without an enforceable mechanism.
- Codex CLI help inspected locally was version `0.153.4`. Flags include JSONL,
  output schema, final-message file, ephemeral execution, sandbox, and additional
  writable directories. Recheck installed/official behavior when implementing;
  help inspection alone did not prove permission parity or auth validity.
- Codex `--add-dir` grants writes. Do not use it to expose read-only memory.
  Triage needs a plan artifact write without general source writes. Reviews
  must not change source or policy. Sandbox write limits alone do not enforce
  command restrictions, MCP isolation, or credential/network separation.
- Capture unique per-phase output outside worker-writable paths; scrub secrets;
  reject stale output, missing terminal events and invalid configured schemas.
- Keep every adversarial review fresh, including when engines differ. Transfer
  explicit artifacts, not author session history. No automatic engine fallback.
- Preserve locks/heartbeats, branch recovery, test gates, final orchestrator JSON,
  read-only status and bot anti-self-trigger behavior. Stop child processes on
  cancellation/timeout before releasing the lock.
- Do not move existing lock/state locations just because they contain `.claude`;
  that could allow old and new dispatchers to race under separate lock domains.
- Installer copies must not strand checkout-relative skill symlinks or place
  caller workflows where GitHub cannot discover them.
- The exposed `sp-*` skills are for explicitly requested orchestration workflows.
  Developing this toolkit does not require invoking `$sp-work 116`. That would
  dispatch workers and publish issue changes, which this handoff does not request.

## Validation and environment

Before runtime changes, inspect prerequisites:

```bash
bash scripts/check-test-prereqs.sh
```

Required runtime checks after appropriate changes:

```bash
shellcheck scripts/*.sh scripts/lib/*.sh
./tests/bats/bin/bats tests/
```

Initialize missing test submodules using `git submodule update --init --recursive`.
Run affected bot/shared pytest suites if those components change. Add behavioral
coverage for CLI construction, normalization, schemas, auth/quota/refusal,
permissions, cancellation, mixed-engine resolution, and duplicate dispatch.

The previous session's default shell sandbox failed before commands ran with
`bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted`. The patch helper
failed the same way. Reviewed `exec_command` escalation succeeded for reads,
branch creation and repository-local edits. This is environment evidence, not
permission to bypass the NEW worker's sandbox or to assume future tool settings.
Use the tools and approval policy available in the new session.

## Remaining questions for live acceptance only

The fixture repository, runner/platform, and paid-run time/spend ceiling are not
yet selected. Obtain those details before the paid GitHub-mutating acceptance
runs; they do not block local implementation or mocked tests. Webber production
workers and its stopped loop must not be switched or restarted by this work.

## Suggested opening prompt for the next session

> Continue implementing issue 116 on `feat/116-codex-worker-engine`. Read
> `docs/superpowers/plans/2026-09-07-codex-worker-engine-handoff.md` and the linked
> implementation plan first. Preserve the existing uncommitted Codex setup.
> The approved first release includes a dispatch-wide default, per-phase
> Claude/Codex overrides, both Codex auth modes, and unchanged independent review
> gates. The #112 asset delivery and normalized Claude adapter milestones are
> complete locally. Continue with engine/model resolution and reachable-phase
> preflight, then the Codex permission proof. Read the continuation evidence
> before starting a completed milestone.
> Continue through local implementation and validation; obtain fixture
> details before live acceptance runs and do not change Webber production.

# Issue 116 implementation handoff

Prepared 2026-09-07. This file transfers the approved design and local work to a
fresh session. Continue from the committed milestones on the existing branch.

## Current handoff checkpoint

Prepared for a new session on the same machine and checkout. The validated
engine/model and reachable-phase preflight milestone is committed as `5b7fb8a`
(`feat: resolve worker engines and preflight reachable phases (#116)`). The
handoff/evidence update is the subsequent commit titled
`docs: prepare Codex worker engine continuation handoff (#116)`.
Use `git log -2 --oneline` to identify both. These commits are local; no push or
PR has been made. Earlier references to uncommitted work are historical.

Current state:

- Claude remains the default and only enabled worker engine. Codex selection
  fails closed until its adapter/policy implementation is ready.
- Engine/model resolution, per-phase overrides, reachable-phase preflight, schema
  snapshots, and semantic failure handling are implemented. Full BATS: 481 pass;
  15 new configuration tests included. ShellCheck and whitespace checks pass.
- The operator approved and installed the standard Ubuntu Bubblewrap AppArmor
  profile. Host sandbox startup and 18 initial no-model boundary checks now pass.
  Reuse this machine's existing STRONGBAD/STRONGMAD/STRONGSAD runners; no new host
  or runner registration is needed for the resolved prerequisite.
- Probe source and results are preserved in
  [sandbox evidence](evidence/2026-09-07-codex-sandbox/README.md), so the next
  session need not rely on `/tmp` artifacts surviving.
- The operator selected **`Frightful-Games/recipe-manager-demo`** for isolated
  acceptance and stated the existing PAT has access. Do not re-ask the repository
  choice. A read-only check with this session's default `gh` credentials could
  not resolve that name, and listing visible organization repositories found no
  recipe match. Before live tests, verify the exact slug and access using the
  intended existing ignored runner configuration/PAT without printing secrets;
  this result does not prove the repository is absent. Do not substitute the
  similarly named local `recipe-manager-setup-demo` checkout automatically.
- The **paid-run time/spend ceiling is still unset**. Obtain it before paid
  model sessions/GitHub-mutating acceptance. The fixture choice does not authorize
  unlimited runs. Local implementation and no-model tests can proceed.

Resume with the remaining permission proof: command restrictions, MCP/hooks/
plugins and project-config inheritance, real worker credential isolation,
nested instruction paths and replacement attacks. Then implement Codex CLI
capability/auth checks, adapter/JSONL normalization and process-tree supervision,
followed by portable assets/workflows and all-Codex/mixed-engine acceptance.
Preserve human approval, fresh independent reviews, locks and semantic outcomes.
Webber production and the operator's authentication remain outside this rollout.

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
The checkpoint predates the engine/model continuation below. Read its current
progress and permission-probe blocker before choosing the next step. No Codex
worker support is claimed.

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

Historical next step at that checkpoint: resolve and freeze engine/model/policy configuration,
including per-phase overrides and reachable-phase preflight; then perform the
Codex capability and permission proof before enabling its adapter. Worker
process-tree supervision, portable worker assets, and isolated live fixtures
remain pending. Webber and the operator's authentication were not changed.

## Implementation progress — engine configuration and permission probe

This continuation is now committed as `5b7fb8a` on
`feat/116-codex-worker-engine`. Issues #116
and #112 still have no comments. No worker model sessions, GitHub mutations,
pushes, commits, or production configuration changes were performed.

- `scripts/lib/agent-config.sh` resolves `AGENT_ENGINE` and phase overrides.
  Engine model defaults are `AGENT_MODEL_CLAUDE` / `AGENT_MODEL_CODEX`, following
  explicit phase models and preceding legacy `AGENT_MODEL`. The legacy fallback
  applies only to the dispatch default engine. REPLY/VALIDATE retain historical
  TRIAGE model inheritance only when their engines match. Recognizable foreign
  model families fail closed; custom IDs remain unchanged.
- Reachability includes reply-to-triage/direct-implementation branches, both
  enabled independent reviews, test fixes, and review retries. Invalid retry
  counts conservatively include the gate's fallback retries. Disabled gates and
  unrelated events do not require their engines. `status` bypasses preflight.
- Dispatch preflight runs under the existing lock before handlers touch
  worktrees. It checks schemas/dependency, Claude CLI/timeout availability,
  local auth status, numeric limits, effort, and permission values. Failure
  records semantic `agent:failed` with process exit zero and a scrubbed diagnostic
  log; tests verify the existing worktree survives and the lock is released.
- Successful preflight freezes engine/model choices and schema JSON in
  `AGENT_PHASE_MAP`, makes worker policy variables readonly, and logs the resolved
  choices. `run_agent` rejects phases absent from this map. The Claude adapter
  consumes the resolved model without introducing another global fallback.
- Readonly shell variables are harness consistency, not worker isolation. Memory
  and MCP file contents, protected capture paths, command/network restrictions,
  CLI optional-flag capability checks, and process-tree supervision still need
  the subsequent adapter/policy milestone. No blanket CLI-version compatibility
  is claimed by the current auth/policy checks.
- Codex is recognized but deliberately disabled in both dispatch preflight and
  direct `run_agent` use. No automatic fallback or unsafe sandbox bypass exists.
- Fifteen behavioral tests in `tests/test_agent_config.bats` cover precedence,
  mixed models, reachability, disabled gates, invalid settings, auth output,
  schema snapshots, and actual isolated entry-point failure/status behavior.

Validation: prerequisites pass with
`PATH="/tmp/sandbox-pal-worker-venv/bin:$PATH"`; ShellCheck and `git diff --check`
pass. The full BATS suite passes all 481 tests (`/tmp/engine-config-full.log`),
including all 15 new configuration tests. The existing BW01 warning remains in
`tests/test_defaults.bats:13`. No bot changes required pytest. These tests use
mock workers and do not establish Codex support.

The installed CLI remains `codex-cli 0.153.4`. Help confirms stdin prompts,
JSONL, final-message files, schemas, ephemeral execution, `--ignore-user-config`,
and `--ignore-rules`. The latter two flags are not proof of project/MCP/hook
isolation. `--add-dir` still grants writes. Top-level approval policy supports
`never`; no model invocation was made to verify effective unattended behavior.

A no-model sandbox smoke probe failed before the command could start:

```bash
probe_dir=$(mktemp -d /tmp/codex-permission-probe-XXXXXX)
codex sandbox -P :read-only -C "$probe_dir" /bin/true
# exit 1: bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted
```

The installed `sandbox` subcommand requires a named permission profile; passing
only the older top-level `-s read-only` exits 2 before execution. The corrected
probe above uses the documented restrictive built-in profile. Evidence is in
`/tmp/codex-permission-probe.log`. This proves an environment startup blocker,
not successful denied-write enforcement. No host policy was relaxed.

Official sources checked on 2026-09-07:
[permission profiles](https://learn.chatgpt.com/docs/permissions),
[sandbox prerequisites](https://learn.chatgpt.com/docs/sandboxing), and
[approvals/security](https://learn.chatgpt.com/docs/agent-approvals-security).
Profiles can describe narrow filesystem boundaries; their domain rules require
an active network proxy. These documented features still need executable hostile
fixtures on a runner where the sandbox starts, including protected paths,
symlinks, credentials, commands, MCP, and project policy inheritance.

Next: continue the remaining permission and CLI capability checks described
below, then the Codex adapter and process-tree supervision. The host sandbox
startup prerequisite is now resolved and initial boundary probes pass. Portable worker
assets and paid all-Codex/mixed-engine acceptance remain pending. The operator
has selected the fixture repository (see current checkpoint); access verification
and spend/time authorization remain before paid/GitHub-mutating runs.

## Local runner assessment — 2026-09-07

The operator confirmed that the existing runners are on this machine. Read-only
inspection found three active Frightful-Games organization runner services:

| Runner | Installation | Service user |
| --- | --- | --- |
| STRONGBAD | `/home/jonny/actions-runner` | `jonny` |
| STRONGMAD | `/home/jonny/actions-runner-strongmad` | `jonny` |
| STRONGSAD | `/home/jonny/actions-runner-strongsad` | `jonny` |

All three listener environments resolve `codex` and `claude` from
`/home/jonny/.local/bin` and `bwrap` from `/usr/bin`. The inspected services have
no private user namespace, namespace restriction, or AppArmor profile override;
the listeners and the host diagnostic process report `unconfined`. No worker
process was observed during the initial process check; this is not a reservation
of any runner or a guarantee that it remains idle.

The host is Ubuntu 24.04.4, kernel `6.8.0-137-generic`, Bubblewrap `0.9.0`.
`kernel.unprivileged_userns_clone=1` and
`kernel.apparmor_restrict_unprivileged_userns=1`. A host-context read-only Codex
probe still fails with `Failed RTM_NEWADDR`; kernel audit records show Bubblewrap
transitioning into `unprivileged_userns`. The configured profile denies namespace
capabilities. No Bubblewrap-specific AppArmor profile is installed, and
`apparmor-profiles` is absent. This points to the documented Ubuntu 24.04
Bubblewrap/AppArmor prerequisite, rather than a missing runner installation.

The Ubuntu `apparmor-profiles` package was downloaded and extracted under
`/tmp/codex-runner-apparmor-review`, without installing it. Its standard
`usr/share/apparmor/extra-profiles/bwrap-userns-restrict` profile allows Bubblewrap
to set up namespaces and drops capabilities in children. `apparmor_parser -Q -T`
validated the profile without loading it into the kernel. The candidate fix is
to install that specific profile at `/etc/apparmor.d/bwrap-userns-restrict` and
load it with `apparmor_parser -r`, then repeat the smoke and hostile-fixture tests.
Do not disable the host-wide user-namespace restriction. Applying the profile is
a host security policy change shared by all three runners. At the time of this
assessment it was pending operator approval; the follow-up below records its
subsequent installation and verification.

A fourth runner on this same host would share the underlying prerequisite. Reuse
the existing installations once enforcement passes, with isolated test artifacts;
a separate VM remains an option if host policy changes are undesirable. Both
CLIs being installed does not establish completed Codex worker support.

## AppArmor fix verified — 2026-09-07

The operator explicitly approved installing/loading the standard Ubuntu
Bubblewrap profile. Automated installation stopped at `sudo` authentication
before any host change. The operator then ran both `sudo install` and
`sudo apparmor_parser -r` commands and confirmed completion.

Verification in host context (outside the interactive session sandbox):

- `/etc/apparmor.d/bwrap-userns-restrict` exactly matches the downloaded Ubuntu
  package profile (`cmp` succeeds). Listing the kernel profile registry is denied
  to the current unprivileged account; effective behavior was tested instead.
- `codex sandbox -P :read-only -C <disposable directory> /bin/true` now exits 0.
  The previous `Failed RTM_NEWADDR` startup failure is resolved.
- `kernel.apparmor_restrict_unprivileged_userns` remains 1. No sysctl was relaxed.
- All three runner services remain active. `claude --version` succeeds with
  `2.1.263 (Claude Code)`; `codex --version` reports `0.153.4`. No paid Claude or
  Codex worker was started, and no authentication was changed.

A no-model Python fixture executed 18 command-boundary checks, all passing:

| Boundary | Observed result |
| --- | --- |
| Built-in read-only profile | Source reads succeed; existing/new source writes fail |
| Explicit implementation profile | Intended source edit succeeds |
| Explicit triage profile | `.agent-data/plan.md` write succeeds; source edit fails |
| Root protected files/directories | Writes to `AGENTS.md`, `CLAUDE.md`, `.agents/`, `.codex/`, `.claude/` fail |
| Symlink targets | Writes through links to protected instructions and external memory fail |
| External memory/capture | Writes fail; memory reads succeed |
| Explicitly denied synthetic credential | Read fails; no real credentials were used |
| Network disabled | Connection denied with permission error to a local listener reachable by the host control |

These were explicit CLI permission-profile overrides applied only to disposable
fixtures. The implementation profile made the root filesystem readable, the
workspace writable, named instruction/policy paths read-only, and a synthetic
credential path denied. The triage profile made only `.agent-data` writable.
Both profiles disabled network. These profiles are probes, not shipped worker
policies; broad root readability is not a complete credential-isolation policy.

Artifacts in this machine's temporary directory:
`/tmp/codex-runner-boundary-probe.py`,
`/tmp/codex-runner-boundary-results.json`, and
`/tmp/codex-runner-boundaries-twton0j6/`. Temporary artifacts may disappear; exact probe source and results are now
archived in [sandbox evidence](evidence/2026-09-07-codex-sandbox/README.md).
These initial probes are not complete release acceptance evidence. `git diff --check` passes for this
handoff-only continuation; the prior full runtime suite remains 481 passing.

Existing runners can now support further Codex sandbox development; a new runner
installation is unnecessary for this prerequisite. This is not yet a completed
Codex adapter or GitHub Actions acceptance run. Remaining proof includes command
policy, MCP/hooks/plugins and project configuration inheritance, scoped/nested
instruction protection, rename/unlink/hardlink attacks, actual worker credential
environment isolation, process-tree cancellation, and model-driven tool paths.
Preserve the Codex execution gate until the adapter and required policies are
verified. No runner services were restarted and Webber production was unchanged.

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

The fixture repository is the operator-selected
`Frightful-Games/recipe-manager-demo`, using the existing PAT. Verify its exact
slug/access with the intended credential context as described above. The
existing Ubuntu runner host is available; select an idle runner when scheduling
tests rather than assuming one is reserved. Obtain the paid-run time/spend
ceiling before paid/GitHub-mutating acceptance. These details do not block local
implementation or no-model tests. Webber production workers and its stopped loop
must not be switched or restarted by this work.

## How to transfer to the next session

On this machine, open a new session in `/home/jonny/repos/sandbox-pal-action` and
paste the prompt below. Stay on `feat/116-codex-worker-engine`; do not recreate
or reset the checkout. The new session should inspect status/logs before edits.
The files and local commits are enough; the old chat history is not required.

For a different machine, transfer the branch commits first: they have not been
pushed. The AppArmor installation and temporary Python venv are host state and do
not transfer with Git. Re-establish prerequisites and rerun sandbox verification
there before relying on this host's evidence.

## Suggested opening prompt for the next session

> Continue issue #116 in `/home/jonny/repos/sandbox-pal-action` on
> `feat/116-codex-worker-engine`. Read
> `docs/superpowers/plans/2026-09-07-codex-worker-engine-handoff.md` first, then
> the linked implementation plan and applicable repository guidance. The
> configuration milestone is committed as `5b7fb8a`; 481 BATS tests pass.
> The existing runner host's AppArmor prerequisite is fixed, and 18 initial
> sandbox checks pass. Resume the remaining permission proof, then the Codex
> adapter and process-tree supervision. Preserve Claude defaults, human approval,
> independent fresh reviews, locks, and semantic outcomes. Use the selected
> `Frightful-Games/recipe-manager-demo` fixture and existing PAT; verify access
> in the intended credential context. Obtain a time/spend ceiling before paid
> acceptance runs. Do not change Webber production or personal authentication.

# Issue 116 implementation handoff

## Current status after merge

The operator merged [integration PR #119](https://github.com/jnurre64/sandbox-pal-action/pull/119)
at `0f717a4967e8d6a0dbbccd09915d0012d8262e40` and Recipe Manager
[SDK repair PR #39](https://github.com/Frightful-Games/recipe-manager-demo/pull/39)
at `e94f2bb169e311082b82cae40fa67075e845fa68` on September 8, 2026 UTC.

The operator explicitly deferred the Claude portion. Both live hybrid directions
are tracked in [follow-up #120](https://github.com/jnurre64/sandbox-pal-action/issues/120).
They do not block the merged integration. Do not retry Claude or request more
subscription budget unless the operator resumes that follow-up. Mocked hybrid
coverage passes; successful live hybrid acceptance is not claimed.

## What is complete

- Explicit Codex and per-phase engine/model routing, with Claude remaining default.
- Native adapter, structured-output conversion, normalized outcomes, cancellation,
  and linked-worktree Git metadata access required for commits.
- Portable shared skills and standalone/reference/custom installation support.
- Generated PRs distinguish earlier worker reports from final dispatcher gates.
- Human plan approval, fresh independent reviews, test and recovery gates remain.
- All 530 BATS tests and ShellCheck passed; log `/tmp/codex-pr-report-final.log`.
  Changed Markdown relative links and whitespace checks passed. Existing BW01 only.
- Real all-Codex triage, human approval, independent plan review, implementation,
  dispatcher test gate, independent post-implementation review, and PR creation
  passed for Recipe Manager #37 → #38. All 15 original final-head tests passed.

## Acceptance PR follow-through

[Recipe Manager PR #38](https://github.com/Frightful-Games/recipe-manager-demo/pull/38)
is open and now includes merged main/SDK repair. Its updated head is
`07245a229d028596032c0e3ffa3e8690711ad4f6`.
[CI run 34175088664](https://github.com/Frightful-Games/recipe-manager-demo/actions/runs/34175088664)
passed SDK setup, restore, build and all 15 tests. PR #38 is ready for human
review/merge. No additional model session or automatic merge was performed.
The initial failed CI run lacked the configured SDK; the separate repair already
passed SDK setup, restore, build and tests before its merge.

## Preserved direction

Match the working Claude integration. Codex support is additive; no production
worker configuration, login, or phase models/budgets were changed. The earlier
30-minute allowance covered only the completed live testing session.
Absolute instruction-file prevention and hostile-process containment are deferred
hardening, not enablement prerequisites. Historical broker/AppArmor experiments
below are superseded, not installed runtime. Do not reopen those scope questions.

See the [live acceptance record](2026-09-07-codex-worker-engine-live-acceptance.md)
and [Claude compatibility baseline](2026-09-07-codex-worker-engine-claude-parity.md)
for detailed evidence and limitations.

## Historical milestones (current direction above takes precedence)

**Historical milestone — actual-CLI no-model adapter checks:** Read the
[CLI integration evidence](evidence/2026-09-07-codex-cli-integration/README.md).
Five actual Codex CLI cases pass through production preflight/adapters: review,
triage plan publication, schema-invalid output, quota error and stalled-response
timeout. A scripted loopback service provides responses without inference. This
validates CLI/adapter integration, not real-provider schemas, tool enforcement,
research, hostile process containment or complete GitHub pipelines. No runtime
files changed; Codex remains disabled. All evidence is local and uncommitted.

**Previous milestone — workflow/reference/custom-install delivery:** Read the
[delivery completion record](2026-09-07-codex-worker-engine-delivery-completion.md).
An explicit client-linking command now connects reference/custom runtimes while
preserving project entries. The distributed configuration example lists all phase
engine/model choices; workflows use the existing shared config-file mechanism.
Most local integration code is implemented. Instruction prevention, actual-CLI
integration/operational proof and separately authorized live acceptance remain
substantive release gates. Prerequisites, ShellCheck and all 525 BATS tests pass.
Codex stays disabled; all changes remain uncommitted.

**Previous checkpoint — native instruction prevention blocker:** Read the
[native instruction decision](evidence/2026-09-07-native-instruction-decision/README.md).
Current documentation does not establish the required cross-engine filename
protection. A new pinned Anthropic sandbox-runtime component probe passes all
10 unconfined controls, but all confined cases fail before command startup; that
is unavailable enforcement, not successful protection or an actual Claude session
result. Prior Codex alias/new-file failures remain applicable. Keep Codex disabled.
Do not repeat unchanged native probes or reopen the withdrawn AppArmor load request.
Continue independent workflow/reference/custom-install delivery while prevention
remains a release blocker. No runtime files, host policy or authentication changed.

**Previous milestone — native configuration compatibility:** Read the
[configuration compatibility record](2026-09-07-codex-worker-engine-configuration.md).
`AGENT_CODEX_USE_NATIVE_POLICY=true` explicitly scopes legacy Claude tool lists,
MCP configuration and turn caps to Claude while Codex uses native policy. Mock
hybrid tests retain real Claude defaults. Dollar budgets and permission modes
assigned to Codex phases still fail closed. The code-defined release gate remains
closed; instruction prevention and live acceptance are unresolved. Prerequisites,
ShellCheck and all 520 BATS tests pass; all changes remain local and uncommitted.

**Previous milestone — standalone client skill delivery:** Read the
[client delivery record](2026-09-07-codex-worker-engine-client-delivery.md).
Standalone setup/update now ship the four shared orchestration skills as
checksummed assets and expose them through portable Claude/Codex discovery links.
Existing project skills and instructions are preserved. Reference/custom install
locations, workflow engine settings, configuration compatibility and instruction
prevention remain release work. Codex stays disabled; no live workers were run.
Prerequisites, ShellCheck and all 516 BATS tests pass. All changes remain local
and uncommitted.

**Previous milestone — phase integration:** Read the
[phase integration record](2026-09-07-codex-worker-engine-phase-integration.md).
Codex is now wired through dispatch preflight and `run_agent` behind a closed,
code-defined release gate. Native phase roles, frozen policy/model/schema state,
shared task context, and harness-side triage plan publication are implemented.
Both hybrid directions and the existing review failure path have mock coverage.
Public Claude-tool configuration compatibility and instruction protection remain
release work; no Codex worker is enabled. AppArmor/broker work remains parked.
Final validation: prerequisites, ShellCheck and all 513 BATS tests pass. All changes
remain local and uncommitted.

**Previous implementation milestone:** [native controls audit and Codex result parser](2026-09-07-codex-worker-engine-native-controls.md).
The native Codex recheck reproduced instruction-protection gaps; Claude defaults
also do not explicitly enforce the requested instruction policy. The new Codex
JSONL normalizer is implemented and tested independently, but no invocation adapter
or Codex enablement is claimed. Prerequisites, ShellCheck and all 490 BATS tests
pass for this milestone. Start with this record before older checkpoints.

**Latest scope — native integration:** The operator requested a simpler,
standard Claude/Codex workflow with research and mixed-phase engines. The
[simplicity review](2026-09-07-codex-worker-engine-simplicity-review.md#updated-scope-ordinary-engine-compatibility)
supersedes the custom-enforcement implementation order and enablement gates below.
The broker, MCP shim, source staging and custom outer sandbox are retired from the
production proposal; their files remain historical evidence. Standard authentication,
Claude defaults and all review gates remain. Both scope questions are settled:
workers must not edit `AGENTS.md` or `CLAUDE.md`; they suggest updates to the
orchestrator, which can apply them or request review. Use native research controls
and preserve project settings, without a new phase-specific access system initially.
Instruction-file prevention still needs verification in both engines. Do not enable
Codex until the required native policy and adapter are verified; report unsupported
protection explicitly rather than restarting the retired custom architecture.


Prepared 2026-09-07. This file transfers the approved design and local work to a
fresh session. Continue from the committed milestones on the existing branch.

## Historical handoff checkpoint — clarified implementation scope

This checkpoint and the [simplicity review](2026-09-07-codex-worker-engine-simplicity-review.md)
are authoritative over the historical continuation instructions below. Both
operator questions have been answered; do not ask them again.

### Decisions to carry forward

- Standard authentication only, using each engine's existing supported login/store.
  No relay, copied credential store or custom refresh implementation.
- Workers cannot edit `AGENTS.md` or `CLAUDE.md`, including nested copies and case
  variants. They submit improvement suggestions to the orchestrator for application
  within its authority or further review. Detection/reversion alone is not prevention.
- Allow research through native engine controls, preserving existing project settings.
  No blanket research/network ban and no new phase-specific access system initially.
  Preserve secret handling; retrieved content remains untrusted input.
- Use native editing and existing worktrees. Broker, MCP shim, source staging and
  custom outer-sandbox prototypes remain historical evidence, not production work.
- Preserve Claude defaults, first-release per-phase engine/model selection, human
  plan approval, fresh adversarial plan/post-implementation reviews, test gates,
  locks, heartbeats, recovery and semantic outcomes. Interactive client selection
  remains independent of worker engine selection.

### Next items to implement, in order

1. **Resolve instruction protection using the smallest supported native mechanism.**
   Read the extended native-profile evidence before repeating probes. Audit both
   Claude and Codex: do not infer that Claude's current tool configuration enforces
   the new requirement. Test protected files at root and nested paths, aliases,
   deletion/parent replacement and new instruction creation, alongside permitted
   source edits and research controls. Treat native tools and shell paths separately.
   If prevention is unsupported, document the exact gap and smallest additional
   option for operator review. Do not silently substitute post-run diff checks,
   restore the custom broker, or change existing Claude defaults. This unresolved
   implementation constraint is not another unanswered preference question.
2. **Implement the Codex adapter behind the existing disabled gate.** Inspect current
   installed CLI capabilities and supported configuration; use standard authentication
   and native settings. Add invocation, JSONL/final-result normalization, schema
   validation, auth/configuration diagnostics, unique scrubbed captures, and timeout/
   process-tree cleanup to the existing neutral interface. Return suggested instruction
   improvements through existing findings/artifacts; keep application with the
   orchestrator. Preserve explicitly configured policies; explain unsupported settings.
   Adapter/result work can proceed while protection remains under investigation.
3. **Integrate preflight and mixed-phase behavior.** Validate only reachable engines,
   retain engine-specific model resolution, and keep author/reviewer contexts fresh.
   Test Claude-only, Codex-only, Claude implementation/Codex review and the reverse.
   Verify research remains usable under the selected native settings. Enable Codex
   only after its required protection and adapter behavior pass; no automatic fallback.
4. **Finish portable delivery and migration.** Ship adapter dependencies, instructions,
   shared skills and workflow settings through the existing setup/update inventory.
   Preserve consuming projects' customizations, Claude entry points and lock locations.
   Explain meaningful engine capability differences without a new permission DSL.
5. **Validate, then perform separately authorized live acceptance.** For shell/runtime
   changes run prerequisites, ShellCheck and all BATS tests; use no-model fixtures
   for policy/adapter behavior first. Use `Frightful-Games/recipe-manager-demo` and
   the intended existing ignored PAT context for live acceptance, after verifying
   access and obtaining the still-unset paid-run time/spend ceiling. Do not substitute
   a similarly named repository or change Webber production or its stopped loop.

### Checkout and validation state

Branch: `feat/116-codex-worker-engine`. Engine/model preflight is committed as
`5b7fb8a`; neutral Claude results and asset delivery are also committed. Codex is
still refused by the shared code-defined release gate. The native adapter,
phase integration and standalone client skill delivery are implemented locally;
read the latest records above for current details. Runtime changes, plans and
extended/broker evidence are uncommitted (some files are untracked); preserve them. No push,
worker dispatch, production change or authentication change accompanied this handoff.

The earlier full runtime result was 481 passing BATS tests plus ShellCheck; it is
historical, not validation of a future adapter. This clarification changes only
documentation: check local links and `git diff --check`. The temporary validation
PATH and runner prerequisite evidence appear below. Recheck their availability
before runtime work; do not rerun custom broker experiments as release gates.

## Historical checkpoint — standard authentication and broker experiments

**Operator direction — standard authentication and simplicity:** Read the
[simplicity review](2026-09-07-codex-worker-engine-simplicity-review.md) before proceeding. Use standard Codex authentication
and its normal credential store/location; leave loading and refresh to Codex.
No custom relay/proxy, token store or refresh implementation unless the operator
explicitly requests it. Credential access by the trusted CLI is allowed; verify
isolation from model-accessible tools and repository/test processes.

The custom broker, outer sandbox and source-export prototypes are experiments,
not required production architecture. Reassess the smallest enforceable design
using standard CLI facilities and the existing worktree lifecycle before expanding
them. The recent prototypes are not referenced by the dispatcher or installer.
This decision supersedes separate-authentication-transport requirements in the
historical checkpoints below. Codex remains disabled and all review gates remain.

Latest continuation: [actual CLI adversarial calls and external broker](evidence/2026-09-07-codex-broker/adversarial-continuation.md)
are now implemented as offline evidence. Sixteen hostile calls were denied across
synthetic and `gpt-5.4` metadata. `gpt-5.4` still exposes direct patching, which
native read-only policy blocks. Two image-read controls fail nested namespace
startup; do not call them passing read checks.

Twelve actual CLI calls reached the harness-owned broker through an explicitly
configured MCP shim and bounded JSON-lines channel. Implementation can make
permitted edits; a fresh review phase cannot. The worker source is exported into
a separate tree with known config/credential paths omitted; the allowed candidate
diff is validated against a harness-owned manifest. Separate test children cannot
reach the live broker socket. Twenty-four portable behavior tests pass.

Four synthetic user/project MCP startup controls match. The hook positive control
did not execute, so **hook isolation is not proven**; its scored probe exits 1.
Plugin/managed hook coverage, standard-authentication isolation, production source
selection/import, phase artifacts and complete process/resource supervision remain
pending. The adapter remains disabled. Continue from the linked record, not the
initial advertised-tool-only checkpoint below. The broker route requires actual
`tool_search` discovery and a namespaced MCP call, plus authorization of exactly
that broker tool; global approval policy and native sandbox remain restrictive.

Validation for this continuation: 24 Python tests, the actual-CLI/broker probes,
Python syntax, evidence consistency, local links and `git diff --check` pass with
the explicit native-read/hook limitations above. Installed runtime files are
unchanged; the 481 BATS/ShellCheck result below is from the prior continuation and
was not rerun for these experimental evidence modules. Everything remains
uncommitted. No model inference, real credentials, GitHub mutations, runner changes,
pushes or personal authentication changes occurred.

### Previous checkpoint — initial broker prototype

Continuation: the [harness-controlled broker spike](evidence/2026-09-07-codex-broker/README.md)
now has a working offline prototype, 10 behavioral tests and 36 matching host
observations (including controls, not 36 release isolation boundaries). Read-only
source plus a serial broker blocks the earlier hardlink, parent replacement and
new-instruction attacks. Synthetic credential files/environment/descriptors,
sibling processes, host listeners and captures are isolated from test children;
a detached child stops on timeout. Named command requests are restricted, but
arbitrary code still runs inside an allowed test sandbox.

A separate scripted local Responses service drove two real CLI invocations
without credentials or model inference, entirely inside the outer sandbox.
Disabling shell/unified execution and related features removed execution and
multi-agent tools from the observed request; `view_image` and
`request_user_input` remained. This is tool-inventory evidence for the synthetic
model ID, not adversarial tool-call enforcement or completed MCP/hook isolation.
See the archived tool results and exact flags in the spike.

**Codex remains disabled.** The broker is experimental evidence, not installed
runtime support. Actual Codex tool routing, both authentication modes through an
isolated transport, safe source export/import, bounded RPC/resource handling and
integrated cancellation remain enablement gates. Extend the local fake-service
probe to hostile actual tool calls before any adapter enablement. Claude defaults,
human approval and fresh independent review gates are unchanged.

Current validation: all 10 new Python tests pass; final host probe exits 0 with
36 matching observations; two offline CLI tool-inventory controls pass;
prerequisites, ShellCheck and all **481 BATS tests** pass. The historical BW01
warning at `tests/test_defaults.bats:13` remains. ShellCheck 0.9.0 was downloaded
as an Ubuntu package and extracted under `/tmp/codex-worker-validation-tools`;
no system installation changed. Use
`PATH="/tmp/codex-worker-validation-tools/extracted/usr/bin:/tmp/sandbox-pal-worker-venv/bin:$PATH"`
for validation in this environment. Full BATS log: `/tmp/codex-broker-bats.log`.
All continuation edits are uncommitted. No paid inference, GitHub mutations,
runner changes, pushes or authentication changes occurred. Prior uncommitted
extended evidence is preserved. Issues #116/#112 were re-read; neither had comments.

### Previous checkpoint — native-profile failures

Continuation after `e6729e0`: the remaining permission proof found reproducible
gaps in the candidate native profile. The new evidence is currently uncommitted;
preserve it. See [extended permission evidence](evidence/2026-09-07-codex-sandbox-extended/README.md).
Twenty no-model boundary checks observed ten enforced and ten unenforced
boundaries/negative controls. In particular, a pre-existing hardlink alias changed
protected instruction contents, an exact nested read rule allowed parent rename
and instruction replacement, and deny globs allowed instructions in newly created
directories. Twelve configuration observations passed their controls, including
the finding that an empty MCP table override does not remove inherited servers
in `codex mcp list`. These are not twelve passing isolation checks.

**Resume with the external-enforcement/mediated-edit design spike in that evidence
record, not native adapter enablement.** The native profile is insufficient for
the approved write-capable policy. Codex remains disabled; no adapter/runtime
changes, commits, paid sessions, GitHub mutations or runner changes were made in
this continuation. Actual worker credential isolation, command policy, MCP/hooks/
plugins, model-driven approval/tool paths and process supervision remain pending.
Issues #116 and #112 were read again and still have no comments. The operator's
live-acceptance time/spend ceiling remains pending.

Validation for this evidence-only continuation: both host probe scripts ran;
the boundary probe intentionally exits 1 for unenforced boundaries, while all 12
configuration observations satisfy their assertions. Python syntax, archived
result consistency, relative evidence links and `git diff --check` pass. The
runtime BATS/ShellCheck suites were not rerun; 481 passing remains historical.
The prerequisite script encounters an npm ShellCheck wrapper first on this
session's PATH, which attempts a download into a read-only global npm directory.
Resolve the validation PATH/tool installation before subsequent runtime edits;
the prior temporary jsonschema venv still exists.

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

Historical next step at `e6729e0` (superseded by the failure evidence above):
resume with the remaining permission proof: command restrictions, MCP/hooks/
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

> Continue issue #116 on the existing branch and preserve all local work. Read
> this handoff's current direction and the Claude compatibility baseline record.
> The user explicitly wants the existing working Claude behavior as the baseline.
> Claude stays default and its adapter/defaults remain unchanged. Codex is selected
> through AGENT_ENGINE/per-phase overrides; production selection and strict wire
> schemas now pass actual-CLI no-model checks. Absolute instruction-file prevention
> and hostile-process containment are deferred hardening, not release blockers.
> Do not revive the broker/AppArmor design or repeatedly ask about these decisions.
> Preserve all human/review/test gates and standard authentication. Assess concrete
> compatibility failures; paid/live acceptance still needs a time/spend ceiling.
> No Webber production changes, login changes, pushes or live dispatch are authorized.

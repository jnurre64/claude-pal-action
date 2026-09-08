# Issue 116: Codex worker engine implementation plan

**Current scope override:** The operator has explicitly selected compatibility
with the existing working Claude integration. Absolute instruction prevention and
hostile-process containment are deferred hardening, not Codex enablement gates.
See [the compatibility baseline](2026-09-07-codex-worker-engine-claude-parity.md).
Earlier stricter release requirements below are historical and superseded.

**Latest milestone — phase integration:** Read the
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


Status: approach approved, including per-phase engine overrides in the first release.

**Current operator decision:** [standard authentication and simplicity review](2026-09-07-codex-worker-engine-simplicity-review.md).
Use Codex's normal login/API-key mechanisms and existing standard credential
storage; Codex owns token refresh. No custom authentication relay, proxy, token
store or refresh implementation unless the operator explicitly requests it.
The trusted CLI may access credentials; isolation is required for model tools
and repository/test processes. Broker, outer-sandbox and source-staging prototypes
are candidates to reassess for necessity, not mandatory production components.
This overrides earlier separate-authentication-transport proposals.
Session handoff: [2026-09-07-codex-worker-engine-handoff.md](2026-09-07-codex-worker-engine-handoff.md).
Repository initialization completed; #112 asset delivery implemented locally
(see handoff progress); neutral Claude adapter and consumer migration implemented
locally. Engine/model resolution and reachable-phase preflight are implemented
in commit `5b7fb8a`. Codex permission proof/adapter remain pending; the
host sandbox startup prerequisite is resolved and 18 initial command-boundary
probes pass; full policy/adapter verification remains pending (see handoff).
Working branch: `feat/116-codex-worker-engine`.
Examined 2026-09-07 at `04cef68` (the same commit cited in the issue).

Continuation after `e6729e0`: [extended permission probes](evidence/2026-09-07-codex-sandbox-extended/README.md)
demonstrate that the candidate native write profile is insufficient. Pre-existing
hardlinks, nested parent replacement and new instruction paths bypass its intended
protections. Keep Codex disabled and prove external enforcement or mediated edits
before the invocation adapter. The linked record preserves 20 boundary results,
12 configuration observations and a concrete candidate for the next design spike.
No runtime support is added by these probes.

The subsequent [broker enforcement spike](evidence/2026-09-07-codex-broker/README.md)
prototypes read-only source, serial mediated edits and isolated test subprocesses.
Ten behavioral tests and 36 host observations match expectations, with explicit
positive/negative controls. Two offline actual-CLI tool-inventory controls also
pass using a local canned response service, without inference or credentials.
The design record evaluates CLI/MCP versus app-server dynamic-tool attachment,
the then-proposed separate model transport, credential-free builds and remaining
enablement gates. The transport proposal is superseded by the operator decision above.
No adapter is enabled: advertised-tool suppression alone is not enforcement,
actual authentication remains untested, and source import/RPC/supervision are
unfinished. Current full validation remains 481 BATS tests plus ShellCheck.

The [actual-CLI continuation](evidence/2026-09-07-codex-broker/adversarial-continuation.md)
adds 16 verified hostile-call denials, 12 successful CLI-to-broker round trips with
phase enforcement, source export/candidate validation and bounded framing (24
portable tests). Four MCP startup controls match; native image-read controls fail
nested sandbox startup and the hook positive control has not executed. These
limitations, standard-authentication isolation and production integration keep Codex disabled.

Issue: https://github.com/jnurre64/sandbox-pal-action/issues/116
Dependency: https://github.com/jnurre64/sandbox-pal-action/issues/112

## Intended outcome

An operator explicitly selects Claude or Codex workers, independently of the
interactive orchestrator client and model. Claude remains the default. Both
engines retain human plan approval, separate adversarial plan and implementation
review sessions, tests, recovery, and reliable semantic dispatch outcomes.
Webber production configuration and its stopped loop are outside this rollout.

## Findings from the current implementation

- `scripts/lib/common.sh:run_claude` builds Claude-specific flags and runs
  `timeout ... claude`. On a nonzero exit it can emit raw output followed by a
  synthetic error object, rather than exactly one internal result.
- `parse_claude_output`, `get_structured_output`, `classify_claude_result`, and
  permission-denial reporting understand Claude envelopes. Semantic failure
  checks are present in some implementation/review paths, not consistently at
  every phase boundary.
- `scripts/sandbox-pal-dispatch.sh` and `scripts/lib/review-gates.sh` directly
  invoke `run_claude` across triage, reply, validation, implementation, PR review,
  adversarial review, test fixes, review retries, and post-merge cleanup.
- `scripts/lib/liveness.sh` already separates semantic `outcome` from process
  `exit_code`. Preserve this public contract; `agent:failed` plus exit zero is a
  controlled failure, not evidence of success. The issue reports a session-limit
  failure for Webber #469; it does not establish the cause of #526.
- Tool settings, label-added tools, MCP configuration, phase permission modes,
  budgets, effort, and max turns are Claude-specific. `AGENT_MAX_TURNS` defaults
  to 200, so preflight must distinguish inherited defaults from explicit settings.
- Memory already accepts configurable files/directories; private Claude memory
  is not mandatory. Its injection and path permissions still need adaptation.
  Worktrees/logs also default to paths under `.claude`; preserve existing state
  locations initially rather than accidentally creating separate lock domains.
- Rules staging copies existing `.claude/rules/*.md` to `.agent-data/rules/` and
  applies selected changes afterward. This is a privileged harness operation;
  it must not become a worker-controlled route to executable configuration.
- The standalone updater tracks scripts, prompts, and labels, omitting schemas,
  skills, and workflow templates. Setup uses an explicit copy list and also
  omits schemas. Issue #112 should own the shared delivery fix.
- Existing documentation contains older handler lists and test counts. Use
  actual scripts, tests, and CI as the implementation baseline.

## Recommended architecture and sequence

### 1. Establish an engine-neutral result contract with Claude first

Introduce `scripts/lib/agent.sh` and engine-specific modules (for example
`engine-claude.sh` and `engine-codex.sh`). Keep them at `scripts/lib/*.sh` so the
current source/copy/lint conventions can include them. Explicitly update the
sourcing chain. Make `run_agent` accept a phase, prompt, model, schema path, and
resolved phase policy; keep engine flag construction inside each adapter.

Emit exactly one versioned JSON envelope on stdout. Suggested fields:

```json
{
  "version": 1,
  "engine": "codex",
  "phase": "TRIAGE",
  "process_exit_code": 0,
  "status": "success",
  "error": null,
  "result_text": "...",
  "structured_output": {},
  "schema_status": "valid",
  "permission_denials": [],
  "denials_available": false,
  "usage": {"input_tokens": null, "output_tokens": null, "cached_input_tokens": null},
  "cost_usd": null
}
```

Use statuses `success`, `failed`, `timed_out`, and `cancelled`; give errors a
separate kind (`auth`, `quota`, `rate_limit`, `permission`, `schema`, `transport`,
`configuration`, `unknown`) and a redacted message. Missing telemetry is unknown,
not zero. A denial record need not mean the entire phase failed; distinguish a
recovered denied attempt from a terminal permission refusal.

Normalize Claude without changing its command flags/defaults. Retain temporary
helper wrappers if needed for compatibility. Move phase consumers to normalized
fields and require semantic success before consuming schema data or advancing a
gate. Keep retry decisions in the harness: auth/quota/configuration failures
stop; transient errors and interrupted useful work follow bounded recovery.
Preserve branches before controlled failures where the current pipeline does so.

Configured but missing, malformed, or unsatisfied schemas must fail closed.
Explicitly disabled schemas may retain documented legacy parsing. Validate the
actual response against the configured schema, not just JSON syntax; choose a
validator and package its dependency in this milestone. Treat this deliberate
change from the current missing-schema warning as a documented compatibility fix.

### 2. Resolve configuration and preflight all phases needed by the event

Confirmed baseline: `AGENT_ENGINE=claude|codex`, default `claude`, selects the
engine for a dispatch. Keep engine selection separate from model selection.
Support both saved Codex login and API key authentication.

The operator also requested the ability to configure both engines and use them
for different phases. Confirmed first-release scope:
`AGENT_ENGINE_<PHASE>` overrides the dispatch default only for that phase.
An unset override inherits `AGENT_ENGINE`; configuring both engines never implies
automatic fallback on quota, authentication, or permission failure.

For example, this proposed configuration uses Claude for implementation and
Codex for the two independent adversarial reviews:

```bash
AGENT_ENGINE=claude
AGENT_ENGINE_ADVERSARIAL_PLAN=codex
AGENT_ENGINE_POST_IMPL_REVIEW=codex
```

Resolve and freeze the effective engine/model/policy map at dispatch start,
including possible test-fix and review-retry phases. Preflight every engine the
event may invoke before starting paid work. A Claude-only event should not need
Codex authentication simply because another event uses Codex.

Model inheritance must not pass a Claude model to Codex or vice versa. Proposed
precedence: explicit phase model, then that engine's default model; the legacy
`AGENT_MODEL` remains a fallback only for phases using the dispatch default
engine. If a different engine has no configured model, use its CLI default.
Define engine-specific default model settings during implementation and validate
explicit model/engine combinations without rewriting model names. Apply the same
capability checks to per-phase effort, budgets, tool rules and permissions.

Record the resolved engine/model per phase. Keep review and retry contexts fresh
across engine changes; exchange only normalized artifacts and finding ledgers.
Extend argv, preflight, recovery and review tests with mixed-engine scenarios;
add a mixed-engine acceptance run alongside the all-Codex fixture. Both authentication modes need coverage, without changing user logins.

After config loading, validate the selected engine, CLI capabilities/version,
schema assets, model/effort configuration, authentication presence, and phase
policies before worktree reset or paid execution. `status` remains usable without
worker authentication. Record dispatch failures through the existing lock owner
and outcome machinery. Preflight can detect missing credentials; revoked tokens
and exhausted quota may only be detected during invocation and must normalize.

Define a capability table: timeout, persistence, schema, sandbox, approvals,
writable paths, network, command policy, MCP, effort, turns, dollars, usage.
Preserve Claude settings. Codex must reject explicitly requested unsupported
Claude controls with actionable diagnostics. Default Claude max turns must not
make every Codex dispatch fail; report Codex's effective limits explicitly.
Never silently discard custom allow/deny rules or label tool additions.

### 3. Prove Codex permission isolation before enabling the adapter

Installed CLI inspected: `codex-cli 0.153.4`, using `codex --help`,
`codex exec --help`, and `codex login --help`. Available exec flags include
`--json`, `--output-schema`, `--output-last-message`, `--ephemeral`, `--sandbox`,
`--add-dir`, and `--ignore-user-config`. This is a candidate verification baseline,
not yet a promised minimum supported version.

Use fresh `codex exec` invocations, prompt via stdin, separate event/final-message/
stderr files, and explicit policy. Parse JSONL terminal events and final message;
never infer success solely from process exit zero or from an intermediate message.
Use unique per-phase artifacts outside worker-writable paths and reject truncated,
missing-terminal, invalid-schema, or stale final output. Scrub secrets before logs
or envelopes are persisted or exposed.

Prove these policies with executable hostile fixtures:

- Triage may write its plan artifact but must not edit the source tree. The current
  nominally read-only phase explicitly permits writing `.agent-data/plan.md`.
  Review phases may read code/diffs and emit findings, but cannot change code or
  their policy. Use read-only source plus a narrowly writable artifact location,
  or have the harness materialize returned plan data if necessary.
- Implementation/fix phases may edit the intended worktree and commit as required,
  with explicit additional writable directories. Codex `--add-dir` grants writes:
  never use it just to expose read-only project memory.
- Protect instruction/configuration files (`AGENTS.md`, `CLAUDE.md`, `.agents/`,
  `.codex/`, `.claude/`) and shared memory from worker policy changes. If intentional
  instruction updates are supported, stage data and validate/apply through the
  harness, including symlink/traversal defenses and review of the applied diff.
- Approval-required operations in unattended phases must refuse deterministically;
  never fall back to bypass flags. Verify the installed CLI's effective approval
  configuration rather than guessing an exec flag from another version.
- Prevent accidental inheritance of personal MCP servers, plugins, hooks, shell
  environment credentials, and permission rules. `--ignore-user-config` alone
  does not prove project policy isolation. Verify all applicable config layers.
- Keep GitHub publishing credentials and label transitions under harness control.
  A writable sandbox alone is not a command allow-list or a network policy.
  Demonstrate deny enforcement for shell commands, MCP, and network separately.

If the installed CLI cannot express the required narrow permissions, use an
external sandbox or restrict supported policies and fail preflight. Do not claim
parity by translating Claude tool strings into broad shell access. Capture the
chosen policy mechanism, platform support, and limitations before implementation.

Supervise the process tree with a wall-clock timeout and TERM/KILL grace period.
Test interruption, ensure descendants stop before releasing the dispatch lock,
and write cancellation/timeout outcomes without duplicate error comments.
No Codex dollar/turn cap is promised without an enforceable supported mechanism.

### 4. Integrate every phase and preserve pipeline semantics

Replace all direct runner calls in dispatch and review-gates. Each review starts
fresh, with only explicit issue/plan/diff/finding context; never resume the author
session. Preserve the human plan approval separately from the two review gates.
Keep finding-ledger dispositions, bounded retries, tests after fixes, unresolved
review reporting, PR review behavior, and post-merge cleanup semantics intact.

Preserve locks, heartbeats, last-dispatch records, status read-only behavior,
branch preservation, and the final orchestrator JSON line. Add engine and phase
error metadata additively if useful; existing `outcome` values remain stable.
Audit bot/workflow consumers and skill instructions for exit-code-only success
checks and duplicate-dispatch races. Keep existing actor filters and bot identity.

### 5. Ship portable assets and coordinate with #112

Repository initialization adds root/scoped `AGENTS.md` guidance and exposes four
existing orchestration skills through `.agents/skills` symlinks. Claude files
remain the shared guidance/skill source. This enables Codex as a client now.

The worker rollout must also audit setup/test/troubleshooting and interactive
recovery skills. For example, the current test skill uses `CLAUDE_SKILL_DIR`, and
`skills/sp-implement` opens a PR before invoking a separate review skill. Do not
blindly expose all skills as equivalent to the gated worker path. Consolidate
portable content without losing Claude entry points or bypassing review gates.

Define one install asset inventory for setup and update: scripts, prompts,
schemas, instruction files, portable skills, and workflow templates. Include
checksums and preserve locally customized files. Templates installed into a
consumer's `.github/workflows` need explicit destination handling; copying them
only inside `.sandbox-pal-dispatch` does not update the caller. Preserve actor
filters. Ensure copied skills do not contain broken checkout-relative symlinks.
Test fresh install and upgrade from pre-schema versions, repeated upgrades, and
EOF/interrupted updates so tracking metadata cannot claim incomplete delivery.

Keep current memory path settings and support a project-owned read-only memory
index/directory. Update setup/docs examples to avoid requiring private session
paths. Handle memory separately from executable configuration and session history.

Document worker engine selection, interactive client independence, authentication,
capability/limit matrix, tested CLI versions/platforms, and recovery diagnostics.
Support both existing login and API authentication, as confirmed by the operator.
Finalize CI credential handling for the chosen fixture runner. Do not expose API credentials to
untrusted test/build subprocesses or alter the operator's personal login.

### 6. Validate before declaring support

- Keep existing Claude command tests; add normalized Claude fixtures including
  `is_error:true` with subtype `success`, caps, partial output and timeout.
- Add Codex argv tests for each phase, paths with spaces, MCP isolation, explicit
  unsupported controls, and no unsafe fallback. Test authentication preflight
  without reading or printing credential contents.
- Add JSONL fixtures for success, structured data, schema failure, auth, quota,
  rate limits, denials/refusal, unknown events, empty/truncated output, cancellation,
  timeout and unavailable usage/cost. Unknown events may be ignored but cannot
  create success. No final output from a previous invocation may be reused.
- Exercise permission boundaries behaviorally, including protected-file writes
  through shell, direct editing, symlinks, external memory, and MCP.
- Extend review, liveness, orchestrator, and installer tests: both gates remain
  independent; semantic failure with exit zero stops advancement; repeated triggers
  do not create duplicate workers/PRs; only the lock owner writes dispatch state;
  recovered branches remain available and status never mutates state.
- Run ShellCheck and BATS, plus affected shared/bot pytest suites when changed.
- Run an opt-in, isolated GitHub fixture through triage, human approval, adversarial
  plan review, implementation, tests, post-implementation review, and PR creation
  using Codex. Verify outcomes, fresh sessions, labels, artifacts, denied writes,
  and a duplicate-trigger attempt. Exercise at least one controlled failure and
  recovery. Record CLI version, policy, auth mode (no secrets), run/PR links and
  results. Mock tests alone do not establish worker support.

## Suggested delivery units

1. Repository initialization and this plan (current change).
2. #112 asset inventory/schema delivery with install/upgrade tests.
3. Neutral envelope + Claude adapter and complete consumer migration.
4. Codex capability/permission proof, configuration and adapter.
5. Portable worker instructions/memory/skills, workflow/auth documentation.
6. Isolated Codex fixture evidence and opt-in release.

Units 2 and 3 can be developed independently. Codex release depends on both,
the permission proof, and end-to-end evidence. No automatic production switch.

## Neutral Claude milestone decisions

The continuation implements the version-1 envelope, all phase consumers and
schema validation. See the handoff for files and verification evidence. The
initial neutral API retains the existing positional argument order to preserve
local callers; production consumers use `run_agent`. The following configuration milestone now resolves engine/model selection;
Codex execution still fails closed pending its permission proof.

The validator is Python `jsonschema>=4.18,<5`, packaged in
`scripts/requirements-worker.txt`. It checks configured schemas before invocation
and structured output afterward. Known drafts and in-document references are
supported without network retrieval; external references are rejected and
`format` remains an annotation. These choices follow the validator's
[validation](https://python-jsonschema.readthedocs.io/en/stable/validate/) and
[registry](https://python-jsonschema.readthedocs.io/en/stable/referencing/)
interfaces. CI and prerequisite checks include the dependency.

Deliberate compatibility fixes: configured schemas cannot silently fall back to
text; every failed decision/review session stops; implementation recovery from
caps/timeouts requires both tests and an independent review. The existing Claude
command flags and process timeout are retained. Process-tree cancellation and
protected capture paths still require the subsequent policy/supervision work.

## Clarifications pending

The dispatch-wide default, first-release per-phase overrides, and both
authentication modes are confirmed. Do not re-ask these scope questions.

The existing Ubuntu host and its STRONGBAD/STRONGMAD/STRONGSAD runners are
available; the standard Bubblewrap AppArmor prerequisite is installed and initial
boundary probes pass. The operator selected `Frightful-Games/recipe-manager-demo`
as the disposable fixture and stated the existing PAT has access. The current
default `gh` credential context could not resolve it; verify the exact slug and
access using the intended existing configuration before live tests. See the
handoff for evidence and constraints.

Still required: an operator-approved paid-run time/spend ceiling before paid,
GitHub-mutating acceptance. Select an idle runner when scheduling the fixture.

These fixture details do not block local implementation or mock-based tests.

## Sources checked

- [Issue 116](https://github.com/jnurre64/sandbox-pal-action/issues/116) and
  [issue 112](https://github.com/jnurre64/sandbox-pal-action/issues/112), plus the
  repository code at `04cef68`.
- [Official non-interactive documentation](https://learn.chatgpt.com/docs/non-interactive-mode):
  `codex exec`, JSONL output, structured final output, and authentication.
- [Official project instruction documentation](https://learn.chatgpt.com/docs/agent-configuration/agents-md):
  root-to-directory `AGENTS.md` discovery.
- [Official skill documentation](https://learn.chatgpt.com/docs/build-skills):
  `.agents/skills` discovery and symlink support.
- Local CLI help at version `0.153.4`; no worker or production dispatch was run.

# Issue 116: phase integration behind the release gate

The configuration limits below describe this earlier milestone. The subsequent
[configuration compatibility record](2026-09-07-codex-worker-engine-configuration.md)
adds explicit native-policy selection; its fixtures retain real Claude defaults.

## Implemented

`agent.sh` now sources `engine-codex.sh` and routes resolved Codex phases to the
native transport. Dispatch preflight validates reachable engines, schemas and
native phase settings, then stores each Codex policy with its frozen model/schema
in `AGENT_PHASE_MAP`. Direct calls also validate policy. Claude invocation and its
existing flags remain unchanged.

The release gate is `agent_engine_enabled`, whose shipped implementation enables
only Claude. It is checked by dispatch preflight, `run_agent`, and the Codex shell
adapter. There is no environment variable to enable Codex. Integration tests
substitute this function only inside isolated shells using mock workers. Test
substitution is not a rollout mechanism and is not evidence of permission enforcement.

| Phases | Native sandbox selection |
| --- | --- |
| TRIAGE, REPLY, VALIDATE, ADVERSARIAL_PLAN, POST_IMPL_REVIEW | read-only |
| IMPLEMENT, REVIEW, POST_IMPL_RETRY, TEST_FIX, CLEANUP | workspace-write |

`REVIEW` addresses PR feedback and may edit; it is not the read-only adversarial
`POST_IMPL_REVIEW`. Every invocation is fresh; no author session is resumed when
switching engines. Existing review schemas, failure classification, label handling,
branch recovery, human approval and test gates remain in their original consumers.

The adapter supplies shared memory as context without granting its directory
write access. It also embeds an explicit whitelist of task environment data as JSON,
so existing prompts remain meaningful without changing Codex's shell environment
policy or copying arbitrary credential/configuration variables into the prompt.
Instruction-update suggestions remain in findings for the orchestrator; the added
prompt instruction is not a filesystem prevention guarantee.

## Triage artifact compatibility

Codex triage stays read-only. The adapter extends the ordinary object response
schema with an internal `plan_markdown` field and tells Codex to return the plan
instead of writing it. After successful normalization/schema validation, the harness
removes that internal field, validates the original response contract, and atomically
writes `.agent-data/plan.md`. The original triage handler then posts the plan and
waits for human approval as before. Question-only responses create no plan artifact.

Missing/empty plans for `plan_ready` fail the phase, so a stale artifact cannot
advance it. Artifact-directory opens use no-follow directory descriptors, and
replacement does not follow a final-file symlink. No arbitrary path is accepted.
The default triage schema is supported, including local references in an otherwise
plain object schema. Custom root composition schemas and an existing reserved
`plan_markdown` property are rejected at preflight; generic schema rewriting is
not attempted. Live structured-output compatibility still requires acceptance.

## Compatibility limits that remain before release

The adapter currently rejects nonempty Claude tool allow/deny lists, requested
Claude permission modes/MCP configuration, explicit Claude turn caps and dollar
budgets. Runtime tool additions are checked again, so label-specific rules cannot
silently disappear after preflight. Native effort, timeout, persistence and writable
directory arguments retain their documented meanings; research/user configuration
is not disabled or rewritten by this integration.

**This is not yet seamless public configuration compatibility.** Existing defaults
include Claude tool rules and the default MCP deny list. The native integration
fixtures explicitly clear those values after loading defaults; that is a test
setup, not a recommended project migration. Before release, define how existing
Claude settings remain scoped to Claude while explicit requested restrictions for
Codex are expressed with supported native controls. Do not silently ignore those
restrictions, weaken existing Claude projects, or add another permission DSL.

Instruction-file prevention and complete containment of processes that deliberately
leave their process group remain unresolved. No custom OS profile, broker, proxy,
source staging or authentication changes were introduced. AppArmor's load request
remains withdrawn. Standard authentication is already implemented; do not restart
that design discussion.

## Validation

The corrected focused suite passes all 35 tests covering phase integration,
transport and engine configuration; initial mock-review schema mismatches were
corrected to use the repository's real action/finding contract. Three additional
behavior cases cover question-only triage, custom-schema rejection and explicit
Claude-only controls. The final full suite passes all **513 BATS tests**, including a strengthened hybrid
case retaining Claude implementation tools while Codex reviews. Prerequisites and
ShellCheck pass. Full log: `/tmp/codex-phase-integration-full.log`. The existing
BW01 warning at `tests/test_defaults.bats:13` remains; that test passes. Python
syntax, local links and `git diff --check` pass. No paid worker, GitHub mutation,
host-policy change, commit or push was performed. Changes remain local.

New tests exercise both hybrid directions, phase roles, frozen model/policy use,
memory/context handling, plan publication failures, unsupported controls, the actual
post-implementation review gate's success/failure paths, and the still-closed
release gate. All workers, authentication checks and GitHub operations in these
tests are mocked. The existing installer inventory includes the new shell adapter
and Python transport; complete setup/update tests remain part of the full suite.

## Next work

1. Resolve the native configuration compatibility described above and the remaining
   instruction-protection contract without reopening parked custom enforcement by
   default. Codex stays disabled until the agreed release requirements pass.
2. Complete portable instructions/shared-skill installation and consuming workflow
   configuration, preserving project customizations and existing lock/state paths.
3. Run actual-CLI no-model integration checks and isolated complete all-Codex/hybrid
   acceptance. Before paid/GitHub-mutating acceptance, obtain the still-unset time/
   spend ceiling and verify intended PAT access to `Frightful-Games/recipe-manager-demo`.
   Webber production and its stopped loop remain outside this rollout.

Phase transport wiring is now implemented; do not repeat that milestone or present
these mock-based integration results as a production-ready Codex worker pipeline.

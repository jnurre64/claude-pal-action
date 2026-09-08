# Issue 116: pre-acceptance review and run preparation

The operator authorized proceeding with review, acceptance fixes and commit/PR
preparation. The operator approved a 30-minute live acceptance session using existing
subscriptions only, with no separately billed API calls. This is a test-session
limit, not a change to phase budgets or models. No new session is required.

## Review completed before acceptance

Reviewed the accumulated engine routing, native policy, schema conversion,
normalization and transport changes. Found and fixed one concrete edge case:
disabling the public triage schema still creates an internal plan schema, but that
fallback omitted the `action` field's type. Added the string type and extended the
existing strict-schema regression case to cover this configuration. Claude's
adapter, defaults and shared schemas remain unchanged.

ShellCheck and all 527 BATS tests pass. Full log:
`/tmp/codex-preacceptance-review-full.log`. The existing BW01 warning in
`tests/test_defaults.bats:13` remains; that test passes. `git diff --check` passes. This is an implementation review, not
the independent worker review that live pipeline phases must still perform.

## Repository verified, read-only

The default interactive GitHub context could not resolve the fixture repository.
The intended existing PAT from `/home/jonny/agent-infra/config.env` resolves exactly
`Frightful-Games/recipe-manager-demo`, with WRITE access, default branch `main`,
and `isArchived=false`. No token value was printed or copied into this record.
Committed configuration selects `pennyworth-bot` and `dotnet test`.

The fixture has active CI/agent workflows and existing workshop/pipeline issues.
Use new dedicated acceptance issues; do not repurpose those issues or replace the
fixture's installed runtime configuration. Run the local candidate with isolated
per-run configuration and existing lock/state behavior. Existing shared approval
and actor-filter rules remain in force.

## Authorized execution order

1. A bounded real-provider smoke invocation using the candidate adapter and a
   shipped schema, in a disposable worktree. Confirm provider acceptance and
   normalized output before spending time on whole pipelines.
2. One small, separately scoped acceptance change for each engine arrangement:
   all Codex; Claude implementation with Codex review; Codex implementation with
   Claude review. Exercise the existing plan approval, fresh independent reviews,
   `dotnet test`, PR and semantic-outcome paths. Stop at human approval holds;
   general test authorization does not itself approve a future generated plan.
3. Fix concrete failures, record results and prepare focused commits/PR. Keep
   historical prototype evidence distinct from shipped runtime changes so the
   review does not imply that the retired broker/OS policy is installed.

Enforce the approved elapsed-time limit and stop between runs to assess remaining
allowance. Codex CLI does not provide a reliable hard dollar cap; do not describe
a configured dollar target as enforced. The approved session runs from 22:47:54 to 23:17:54 UTC on September 7.
An outer timeout enforces that deadline while normal worker timeout remains 3600
seconds, matching the demo configuration. Stronger instruction prevention remains deferred and is not being reopened.

## Live progress

See the [live acceptance record](2026-09-07-codex-worker-engine-live-acceptance.md)
for actual provider results, issue links and outstanding human approval.

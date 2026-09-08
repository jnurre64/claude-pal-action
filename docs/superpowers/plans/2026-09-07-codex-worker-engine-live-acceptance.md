# Issue 116: live subscription acceptance

The operator authorized live tests against `Frightful-Games/recipe-manager-demo`
for 30 minutes, using existing subscriptions and no separately billed API calls.
Session: September 7, 2026, 22:47:54–23:17:54 UTC. This allowance applies to the
acceptance session; it does not flatten phase models or budgets. The demo has
`AGENT_TIMEOUT=3600`, `AGENT_TEST_COMMAND="dotnet test"`, and no explicit phase
model or dollar-budget overrides. Those settings are retained for the pipeline.
An outer timeout bounds dispatches to the remaining acceptance time.

## Environment and isolation

- Candidate runtime runs directly from this branch, with disposable configuration
  and worktrees. The installed demo runtime and existing issues are untouched.
- Existing shared issue locks remain in use. External notification backends are
  disabled for the fixture. GitHub issue/PR operations are part of the live test.
- Codex ChatGPT and Claude subscription logins were verified without changing
  authentication or printing credentials. API-key environment overrides are unset.
- Baseline main commit: `3190250`. `dotnet test` passed all 10 existing tests.

## Results

1. A real-provider Codex read-only smoke passed: native reads of `CLAUDE.md` and
   the test project, strict review schema accepted, normalized status `success`
   with approved review output. The short 180-second smoke timeout is test-only.
2. Dedicated all-Codex [issue #37](https://github.com/Frightful-Games/recipe-manager-demo/issues/37)
   requests one new Recipe.Name validation test file. Real dispatcher triage
   returned `agent:plan-review`, exit 0, and published the
   [implementation plan](https://github.com/Frightful-Games/recipe-manager-demo/issues/37#issuecomment-5576393193).
   This verifies real triage publication and the human approval hold. It is not
   a completed implementation pipeline.

3. The unchanged Claude adapter was also exercised through a subscription smoke.
   It returned normalized `status=failed`, `process_exit_code=1`,
   `error.kind=rate_limit` (the shell wrapper itself exited zero). This does not
   establish successful Claude or hybrid acceptance. Defer mixed-engine runs
   until subscription capacity is available; do not switch to billed API calls.

The user approved the generated plan and applied `agent:plan-approved`; this was
verified on GitHub at 22:57 UTC. The candidate implementation dispatch began at
22:57:45 UTC and its fresh adversarial plan review approved the plan at 22:58:24.
No merge is authorized. The first candidate implementation failed at the commit
gate: file edits succeeded, but native workspace-write blocked Git metadata writes.
The worker also reported .NET test-runner socket denial. The dispatcher returned
`agent:failed` despite process exit zero and removed the uncommitted worktree.

A disposable real Codex probe proved that explicitly adding the Git common directory
as a native writable path permits commits. The adapter now resolves both Git
metadata directories for editing invocations and passes them through `--add-dir`.
Advisory phases gain no Git write access. Prerequisites, ShellCheck and all 528
BATS tests pass (existing BW01 warning only). Full log:
`/tmp/sp116-live-VsD4zb/git-fix-full-tests.log`. This is standard native directory
configuration, with no broker, host policy or Claude adapter change. See the
[official sandbox configuration guidance](https://learn.chatgpt.com/docs/sandboxing).

The already-approved plan was retried at 23:03:35 UTC with fresh reviews intact.
The retry completed at 23:06:29 UTC with `outcome=agent:pr-open`, `exit_code=0`,
and [PR #38](https://github.com/Frightful-Games/recipe-manager-demo/pull/38).
The pre-PR test gate passed; a fresh Codex post-implementation review approved with
no findings and no retry sessions. The final PR contains the new test file plus
the existing pipeline's review ledger. Final head:
`c61d09a758103389626215b30cb4afebc14007db`.
Independent `dotnet test` on that exact head passed all 15 tests.

GitHub [CI run 34168892170](https://github.com/Frightful-Games/recipe-manager-demo/actions/runs/34168892170)
failed before tests: the selected runner lacks `/home/jonny/.dotnet/dotnet`.
This is unresolved CI infrastructure, not a passing CI claim. No workflow or
runner configuration was changed. The token cannot read GraphQL statusCheckRollup;
Actions run/log endpoints supplied the failure evidence.

The generated PR description retained legacy Claude attribution and the worker's
pre-gate test limitation. It was corrected for this fixture with actual engine,
review, final-head test and CI outcomes. Generic PR description generation was subsequently fixed: it now uses
engine-neutral attribution, separates the earlier worker report, and reports
passed/disabled/unresolved final dispatcher gates. Behavioral regressions cover
both engines and non-passing gate configurations.

The approval label also triggered the demo's installed Claude workflow
[run 34168401957](https://github.com/Frightful-Games/recipe-manager-demo/actions/runs/34168401957).
It reached adversarial review, hit the Claude weekly limit, posted an error, and
returned a green workflow despite that failed review. This is the installed
runtime's outcome, not the candidate Codex run. Both were briefly active: the
candidate's configured lock domain did not prevent this installed-workflow overlap.
Subsequent label-triggered runs completed/cancelled/skipped; an attempted cancellation
of the last apparent active triage run found it already completed and skipped.
Do not describe this acceptance as proof of cross-installation lock exclusion.
Avoid GitHub approval-label dispatches for future local fixtures; approve the
specific generated plan in-session and invoke the candidate dispatcher directly.
Hybrid runs remain deferred because Claude subscription capacity is unavailable.

Transient local logs: `/tmp/sp116-live-VsD4zb/` (`baseline-tests.log`,
`smoke-result.json`, `smoke.log`, `smoke-claude-result.json`,
`smoke-claude.log`, `triage37.stdout`, `triage37.stderr`).
No authentication material is included in this record.

Durable summary: [acceptance evidence](evidence/2026-09-07-live-codex-acceptance/results.json).
Full local final-head test output: `/tmp/sp116-live-VsD4zb/pr38-final-tests.log`.

## Follow-up CI repair

[Draft PR #39](https://github.com/Frightful-Games/recipe-manager-demo/pull/39)
provisions .NET 9 in the runner temporary directory through setup-dotnet, removing
the hard-coded SDK dependency. It is separate from #38 and has not been merged.
[CI run 34174370640](https://github.com/Frightful-Games/recipe-manager-demo/actions/runs/34174370640)
passed SDK setup, restore, build and tests. #38 still needs the merged workflow
fix before its own CI can be rerun reliably. No additional model sessions were
run during this review-preparation work.

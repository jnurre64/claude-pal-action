# Issue 116: explicit native configuration compatibility

The adapter now accepts `AGENT_CODEX_USE_NATIVE_POLICY=true` as an explicit
selection of native Codex policy. This resolves the conflict between keeping
Claude's existing defaults and running mixed phases without pretending that
Claude tool strings are enforceable Codex permissions.

With this selection, Claude allow/deny lists, extra and label-specific tools,
MCP configuration/strictness and turn caps remain scoped to Claude. Codex uses
the adapter's native phase sandbox and its existing native integration/research
configuration. No new permission language, broker, authentication mechanism or
project configuration rewrite is introduced. Claude's adapter is unchanged.

Selection defaults to false. Without it, conflicting legacy controls still fail
Codex policy validation. This is deliberate migration acknowledgement: projects
that require those restrictions must verify equivalent supported native controls
before selecting native policy. Merely renaming a Claude setting would not provide
that guarantee. The setting is not a Codex enablement switch.

Preflight logs the scope difference and freezes the selection with the phase's
native policy. Invocation uses the frozen field when evaluating its tool argument,
including tool additions from labels. The shell-only selection field is removed
before constructing the Python transport request. It does not change native CLI
configuration or grant additional directories. Direct `run_agent` calls validate
the same selection; unused Codex settings are not validated for Claude-only work.

Dollar budgets remain a hard error on reachable Codex phases, including a global
budget. `AGENT_PERMISSION_MODE_<PHASE>` also remains a hard error when assigned to
a Codex phase. These settings express a limit for that phase, and native-policy
selection does not waive them. Timeout is elapsed time, not a turn or dollar cap.

The configuration reference and example defaults document the migration and a
staged hybrid example. Existing tool configuration values do not need to be cleared.

## Validation and remaining work

The corrected focused 16-test phase suite passes. It exercises actual Claude
defaults in both hybrid directions, native scoping of configured MCP/turn/label
tools, frozen selection, strict migration rejection and unsupported phase limits.
The full suite, including a further Claude-only reachability case, passes all
**520 BATS tests**. Prerequisites, ShellCheck, local milestone/handoff links and
`git diff --check` pass. Full log: `/tmp/codex-configuration-full.log`. The existing
BW01 warning at `tests/test_defaults.bats:13` remains; that test passes.

Workers, authentication and GitHub calls in these fixtures are mocked. This proves
harness configuration behavior, not effective native permission enforcement or
production readiness. Codex remains disabled by the shared code-defined gate,
even with native policy selected. All edits are local and uncommitted; no paid
worker, dispatch, GitHub mutation, authentication or host-policy change occurred.

Next: resolve required instruction-file prevention without silently relaxing it
or reviving retired custom enforcement. Complete workflow engine settings and
reference/custom-location delivery, then actual-CLI no-model checks. Paid/hybrid
acceptance still requires the operator's time/spend ceiling and intended PAT access
verification for `Frightful-Games/recipe-manager-demo`.

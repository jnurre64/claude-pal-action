# Issue 116: workflow configuration and remaining client delivery

Added `scripts/link-client-skills.sh <project> <runtime>` for reference and custom
installations. It verifies the runtime has the dispatcher and four shared skills,
then creates a relative `.sandbox-pal-dispatch` alias and reuses the existing
Claude/Codex client discovery helper. Existing installations pointing elsewhere
fail without replacement; existing client skill entries are preserved.

An in-project runtime and all its links move together. An external reference
runtime is deliberately a local connection: the command says to keep the runtime
alias local and recreate it elsewhere. It does not disguise an external checkout
as a portable copied installation. Source assets stay at the runtime's original
location, so their existing update/checksum mechanism continues to apply. Both
clients see canonical updates immediately; rerunning the command repairs missing
discovery links. Setup's reference-mode summary prints this explicit connection
path and reminds the operator to select the intended project configuration.

No client instructions or shared skill text changed. No credentials, source tree,
locks or state were moved. The helper ships in the existing scripts inventory.

## Workflow configuration delivery

The existing workflows already support a common configuration file; another
workflow permission format or set of duplicated per-phase inputs is unnecessary.
The distributed example now lists global engine/model defaults and every supported
phase's engine/model overrides. Entries are commented so delivery cannot enable
Codex. Setup/update discover these through the existing configuration inventory.

The configuration guide explains the supported paths:

- Standalone label and programmatic callers use the same dispatcher, committed
  `config.defaults.env` and optional ignored `config.env`.
- Reference callers use the existing `dispatch_script` and `config_path` inputs;
  use absolute runner paths and the same project config for all events.
- Template upgrades remain reviewable reference assets. Existing actor filters,
  workflow concurrency and human approval gates are preserved.

Workflow YAML behavior did not change. The current reusable dispatch workflows
were inspected for their `AGENT_CONFIG: inputs.config_path` wiring, along with
standalone and programmatic caller templates. Runtime engine/model resolution and
reachable-phase behavior retain their existing tests.

## Validation

Prerequisites and ShellCheck pass. Four focused client-link tests pass, covering
external references, movable custom runtimes, missing/conflicting assets and local
skill preservation. A new end-to-end updater test verifies every phase setting is
tracked without replacing project engine/model choices or enabling native policy.
All **525 BATS tests** pass; log: `/tmp/codex-delivery-completion-full.log`.
The existing BW01 warning at `tests/test_defaults.bats:13` remains; that test
passes. Local documentation link targets and `git diff --check` pass.
No worker, GitHub mutation, authentication or host-policy change was performed.
All changes remain local and uncommitted.

## Remaining release work

Most local integration code is implemented: transport/result handling, preflight,
mixed phases, explicit native configuration and client/asset delivery. This is not
equivalent to a nearly enabled release. The remaining gates are substantive:

1. Required instruction-file prevention has no verified native solution; see the
   [decision checkpoint](evidence/2026-09-07-native-instruction-decision/README.md).
   Keep Codex disabled and do not repeat unchanged probes or reopen parked custom
   enforcement without an explicit new scope decision.
2. Actual-CLI no-model adapter/phase integration and operational acceptance remain.
   Mock tests do not verify live structured-output compatibility, native research,
   credential boundaries or containment of children that leave their process group.
3. Isolated all-Codex and both hybrid acceptance runs remain. Before any paid or
   GitHub-mutating run, obtain the time/spend ceiling and verify intended PAT access
   to `Frightful-Games/recipe-manager-demo`. Webber remains outside this rollout.

Continue with bounded actual-CLI no-model checks where useful. Report unavailable
boundaries precisely; do not mark the overall issue complete while these gates
remain unresolved.

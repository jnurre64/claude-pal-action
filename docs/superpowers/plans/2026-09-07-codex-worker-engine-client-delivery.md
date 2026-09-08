# Issue 116: standalone client skill delivery

The shared standalone inventory now includes the canonical `sp-work`, `sp-status`,
`sp-revise` and `sp-post-merge` skill directories under `.claude/skills/`. Setup
and update install ordinary files under `.sandbox-pal-dispatch/.claude/skills/`,
with the same checksums and local customization handling as runtime assets.
The repository's `.agents/skills/` symlinks are not copied.

Both installers expose those installed sources through relative directory links
in the consumer's `.claude/skills/` and `.agents/skills/`. The links survive moving
the entire consumer checkout, and both clients read the same installed source.
Existing entries, including dangling links, are preserved with a diagnostic.
Symlinked client directory parents are not traversed when creating links. Deferred
or missing skill sources do not create dangling discovery links. Updates repair
missing discovery links once the source exists. The links are deterministic
discovery entries; `.upstream` tracks their canonical source files.

Project `AGENTS.md` and `CLAUDE.md` are neither created nor replaced. Repository
development guidance is not copied into the consumer's root instructions. The
customization guide explains the client entry points, conflict handling and which
paths to commit. Shared skill text and its human approval/semantic-outcome rules
are unchanged. This is asset delivery, not a dispatch or instruction-protection
implementation.

## Deliberate limits and next work

- Automatic discovery links support the standard `.sandbox-pal-dispatch` location
  used by the skill text. Reference-mode and custom-location client configuration
  remain pending; no absolute link to this development checkout is installed.
- Workflow templates continue to use the existing inventory and setup rendering.
  Engine-setting migration in consuming workflows remains pending. Updates report
  template changes for review rather than overwriting consumer workflows.
- Native configuration compatibility is still unresolved as described in the
  [phase integration record](2026-09-07-codex-worker-engine-phase-integration.md).
  Default Claude tool lists currently prevent seamless mixed-engine configuration.
- Required instruction-file prevention remains unsupported by the verified native
  profile. Codex stays disabled. Retired custom enforcement experiments remain
  parked; this milestone makes no new permission or process-containment claim.
- Paid acceptance still needs a time/spend ceiling and verified intended PAT
  access to `Frightful-Games/recipe-manager-demo`. No live worker, GitHub mutation,
  authentication change, host-policy change, commit or push accompanies this work.

## Validation

Prerequisites and ShellCheck pass using the existing temporary validation tools.
All 49 focused installer tests pass, including expanded fresh-setup coverage and
three new behavioral tests for upgrade/move/customization, linked parents and
deferred delivery. All **516 BATS tests** pass; the full log is
`/tmp/codex-client-delivery-full.log`. The existing BW01 warning at
`tests/test_defaults.bats:13` remains; that test passes. Local handoff/milestone
link targets and `git diff --check` pass. All changes remain local and uncommitted.

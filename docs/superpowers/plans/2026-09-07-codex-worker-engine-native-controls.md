# Issue 116: native controls audit and result parser milestone

## Decision and scope

Continue with standard authentication, native research controls and existing
worktrees. Workers must not modify AGENTS.md/CLAUDE.md; suggestions go to the
orchestrator. No custom broker, model relay or source staging was added. Codex
remains disabled in dispatch preflight and `run_agent`. Claude invocation and
configuration defaults remain unchanged.

## Native instruction protection is still unresolved

Installed versions checked: Codex 0.153.4 and Claude Code 2.1.263. Re-ran the
[existing native probe](evidence/2026-09-07-codex-sandbox-extended/probe.py)
in host context using disposable `/tmp` fixtures and synthetic credentials only.
The [new report](evidence/2026-09-07-codex-sandbox-extended/native-recheck-results.json)
again records 20 observations, with 10 matching the proposed boundary and 10 not
matching (including negative controls). The expected probe exit is 1.

| Codex tested operation | Result |
| --- | --- |
| Root instruction unlink/replacement | Denied |
| Pre-existing hardlink alias | Instruction content changed through alias |
| Both hardlink paths explicitly protected | Write denied |
| Exact nested instruction path | Direct write denied |
| Rename writable parent and replace instruction | Allowed |
| Explicit writable parent mount plus protected child | Tested parent replacement denied |
| Create instruction inside a new directory with deny glob | Allowed |

These are sandbox-command observations, not model-driven acceptance. The native
profile is not sufficient for the full requested instruction-file contract.
Enumerating exact paths/parents and rejecting hardlinks could address some cases,
but does not solve arbitrary new instruction paths; do not describe it as complete.
Codex documents pre-expanded deny-read globs on Linux and separates command-network
enablement from domain filtering. Those controls do not establish a dynamic
filename write prohibition. [Codex permissions](https://learn.chatgpt.com/docs/permissions).

The current Claude adapter passes the existing broad Edit/Write allowances and
operator deny-tool settings; the default deny list is `mcp__github__*`. It does
not inject AGENTS.md/CLAUDE.md deny rules or require a filesystem sandbox. Personal
or project settings may add restrictions, so this is a repository-default audit,
not a claim about every installed project. No real Claude worker was invoked.
Claude documents native Edit path-deny rules, including coverage of some recognized
shell file operations, but arbitrary Python/Node subprocess writes require sandbox
enforcement. The published sandbox protected-path list does not establish protection
for these instruction filenames. Actual alias/replacement cases remain unverified
for Claude. [Claude permissions](https://code.claude.com/docs/en/permissions),
[Claude sandbox](https://code.claude.com/docs/en/sandboxing).

Do not add nominal Edit deny rules and call the cross-engine requirement met.
Do not silently tighten existing Claude defaults or disable research to compensate.
Native web research and shell-network access are distinct; preserve the project's
explicit settings rather than inventing universal equivalence between engines.

### Smallest next enforcement investigation

No complete stock CLI configuration meeting the full contract has been established.
Before reviving any custom editing service, assess a small standard OS policy
applied to the worker and descendants (for example a narrowly scoped AppArmor
policy on the existing Ubuntu host). It must cover built-in edits, subprocesses,
aliases and parent replacement while permitting normal source edits and research.
This is an unverified, Linux-specific candidate requiring host-policy review, not
an approved implementation or a guarantee that simple pathname denies suffice.
No profile has been installed or changed. If it cannot be made small and reliable,
report that conflict between strict prevention and stock CLI behavior explicitly.
The retired broker is not an automatic fallback.

## Implemented: Codex JSONL result normalization

Added `normalize-codex` to `scripts/lib/agent-result.py`, reusing existing schema
validation, secret scrubbing, failure classification and the version-1 envelope.
This is result-processing code only; it launches no engine and opens no execution
path around the existing Codex gate.

It requires one started thread/turn, a terminal turn event and a nonempty final
agent message matching the separate final capture. Comparison precedes redaction.
Malformed/truncated streams, duplicate turns/terminal events, missing captures and
mismatched text cannot succeed. Turn/stream failures override useful output even
at process exit zero. Individual failed commands and metadata warnings can recover
within a subsequently successful turn. Schema-enabled results must parse as JSON
and pass the configured schema. Unknown cost and denial telemetry remain unknown.

The future invocation adapter must create unique private captures and enforce
process supervision; matching content alone cannot prove file freshness. No
invocation, authentication preflight, cancellation supervisor or mixed-engine live
support is claimed by this milestone. Native event fields and final-output behavior
were checked against [Codex non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode)
and 18 archived actual-CLI event streams. For archive compatibility only, final
captures were reconstructed from their last agent messages; this is not freshness
or current live-authentication proof.

## Validation

Prerequisites, ShellCheck and all **490 BATS tests** pass, including nine new
Codex result tests and the existing Claude/dispatch/install suites. The historical
BW01 warning in `tests/test_defaults.bats:13` remains; that test passes. Full log:
`/tmp/codex-native-adapter-bats.log`. Local links and `git diff --check` pass.
The native host probe intentionally fails its stricter boundary assertions as
reported above. No paid inference, GitHub mutation, runner reconfiguration or
personal authentication change occurred.

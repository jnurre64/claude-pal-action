# Issue 116: native Codex transport milestone

**Subsequent milestone:** [phase integration](2026-09-07-codex-worker-engine-phase-integration.md)
now connects this transport behind the closed release gate. Statements below about
unconnected transport describe the earlier milestone, not current wiring.

## Current direction

The operator asked to proceed with other remaining work after questioning custom
OS enforcement. The AppArmor experiment is parked and its load request withdrawn.
No experimental policy was loaded. Do not require that experiment to continue
adapter development, and do not interpret the request as waiving instruction-file
protection. The public Codex execution gate remains closed.

## Implemented

`scripts/lib/codex-worker.py` is the internal native CLI transport. It accepts a
JSON request through stdin and launches fresh `codex exec` sessions with the prompt
on stdin, explicit read-only/workspace-write mode, unattended approval policy,
JSONL and a separate final-message capture. It uses the existing result normalizer.
Normal user/project configuration and rules remain loaded; research controls are
not overridden. Model, effort, extra writable directories and session persistence
map to native settings; schemas use the existing validator and native output-schema
flag. This is transport plumbing, not a new public project configuration interface.

Preflight checks required exec capabilities and either the documented exec-only
`CODEX_API_KEY` override or `codex login status`. It does not open/copy authentication
files, log identity, change HOME/CODEX_HOME, perform login, refresh tokens itself,
or introduce a proxy. Presence of credentials is not verification against revoked
credentials or exhausted quota; invocation errors still normalize separately.
See [Codex non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode)
and [standard authentication](https://learn.chatgpt.com/docs/auth).

Each invocation uses a fresh private capture directory outside the worktree. The
final file must be a regular, single-link file and cannot be followed through a
symlink. Raw events, final text and schema captures are removed after normalization;
only the normalized result and scrubbed stderr remain. Private filesystem modes
protect against other users, not hostile processes running under the same user.
Do not claim that file permissions provide the unresolved isolation guarantees.

The transport creates a POSIX process group, forwards cleanup through TERM then
KILL, and reaps its direct child on timeout/cancellation or normal completion.
Tests include stubborn descendants and a parent that finishes while a child remains.
Processes that deliberately leave the group via setsid are not covered; complete
process-tree containment remains an integration concern, not a guarantee here.
No full OS sandbox, credential isolation system or custom edit interface was added.

Unsupported request keys are rejected. This avoids silently accepting Claude tool
rules, dollar budgets or other restrictions that this transport does not enforce.
The future phase adapter must resolve/report such capability differences before
invoking this module. In particular, the transport's sandbox argument is explicit;
this module does not decide phase permissions or enforce instruction immutability.

## Validation and limits

Ten new transport BATS tests and the existing result/agent tests pass (39 focused
tests total). They use a mock executable and synthetic credentials, with no model
calls. Coverage includes stdin/argv/config preservation, authentication/capabilities,
schemas, unsupported settings, capture hygiene, failures, timeout, cancellation,
descendant cleanup and both existing Codex execution gates. Installer inventory
coverage now includes the transport; the shared inventory supplies setup and update.
Prerequisites, ShellCheck and all **500 BATS tests** pass. Full log:
`/tmp/codex-transport-full.log`. The existing BW01 warning at
`tests/test_defaults.bats:13` remains; that test passes. Local links, Python syntax
and `git diff --check` pass. No paid model calls or host changes were made.

The transport is deliberately not sourced or called by `agent.sh` or dispatch.
CLI capability/auth checks remain internal and are not required for Claude-only
work. No runnable Codex pipeline, live engine integration, instruction-file
protection or paid acceptance is claimed by this milestone.

## Remaining integration

1. Connect resolved phase settings and prompts/shared memory to the native transport
   behind the closed public gate, with explicit diagnostics for unsupported policies.
   Carry instruction improvement suggestions in existing findings/artifacts for the
   orchestrator; do not let workers apply them directly.
2. Settle the unresolved instruction-protection contract without restarting custom
   OS/broker work by default. Preserve Claude compatibility and review-only policies.
   Validate complete cancellation/descendant handling before releasing dispatch locks.
3. Exercise all-Codex and mixed Claude/Codex phase routing through dispatch and review
   gates; preserve fresh contexts, human plan approval and semantic failures.
4. Finish portable client instructions/skills and workflow configuration delivery,
   preserving consuming project customizations and existing lock/state locations.
5. Perform isolated live acceptance only after the remaining gates pass and the
   operator supplies the still-unset time/spend ceiling. The selected fixture remains
   `Frightful-Games/recipe-manager-demo`; do not change Webber production.

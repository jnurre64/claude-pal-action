# Harness-controlled edit broker spike — 2026-09-07

**Historical evidence, not the current implementation roadmap.** The operator
requested native engine integration and removal of unnecessary custom complexity.
The [updated scope](../../2026-09-07-codex-worker-engine-simplicity-review.md#updated-scope-ordinary-engine-compatibility)
retires custom broker/source-staging/outer-sandbox work from the production proposal.
Results below remain observations of the tested profiles; their stronger policy
assumptions and “next steps” are superseded. Do not resume these experiments as
mandatory adapter work.

**Current direction:** [standard authentication and simplicity review](../../2026-09-07-codex-worker-engine-simplicity-review.md)
supersedes earlier relay/transport proposals. Use normal Codex authentication;
a custom relay is out of scope unless explicitly requested. This broker and its
outer sandbox/source-staging modules are experimental candidates, not a committed
production architecture. The source/results below remain historical evidence.

Current continuation: [actual CLI tool calls and external broker evidence](adversarial-continuation.md)
now demonstrates 16 hostile-call denials and 12 real CLI-to-broker calls across
implementation/review. Source export, candidate validation and bounded framing
have 24 portable tests. Native image reads and the hook positive control fail;
authentication and production integration remain pending. The sections below
preserve the initial design/probe checkpoint; use the continuation for current
results and next work.

**Decision: continue with mediated edits; do not enable Codex yet.** The offline
prototype closes the demonstrated native-profile write bypasses for its tested
source tree. It also demonstrates synthetic credential/process/network isolation
for test subprocesses. It does not establish actual Codex tool enforcement or
model authentication isolation. No adapter, installed asset, runner service,
personal authentication, Claude default, or review gate changed.

This follows the [extended native-profile evidence](../2026-09-07-codex-sandbox-extended/README.md).
Both GitHub issues were read again; #116 and #112 still had no comments.

## Reproduce and evidence

From this directory:

```bash
python3 test_prototype.py
# 10 behavioral tests, including parameterized attack/phase cases.
python3 probe.py > /tmp/codex-broker-proof-results.json
# Run in host context; exit 0 only when every expected observation matches.
python3 tool-probe.py > /tmp/codex-broker-tool-results.json
# Host context; the CLI and fake response service are confined together.
```

[prototype.py](prototype.py) contains the edit/command interfaces and external
sandbox launcher. [test_prototype.py](test_prototype.py) uses disposable trees
without Bubblewrap. [probe.py](probe.py) runs hostile fixture code with synthetic
credentials and localhost listener controls. It invokes no model or Codex session.
[results.json](results.json) archives the final host run: **36 expected
observations**, including positive controls and one deliberate arbitrary-shell
negative control. This is not 36 passing release security boundaries.

Host: Ubuntu 24.04, Bubblewrap 0.9.0, Python 3.12.3. The existing AppArmor
prerequisite suffices; no host security configuration was changed. An intermediate
probe failed startup because `--disable-userns` requires explicit `--unshare-user`
even with `--unshare-all` on this version. The final launcher includes both and
fails closed on startup errors. Do not remove namespace restrictions to recover.

| Mechanism | Observed behavior |
| --- | --- |
| Read-only source mount | Reads succeed; direct source, root/nested instruction, unlink, rename, new directory/instruction writes fail |
| Alias protection | Pre-existing hardlink, symlink, scratch symlink and `/proc/self/root` write attempts fail; new hardlink into scratch fails |
| Broker mutation | Authorized source edit is visible in a subsequent sandbox; original instruction contents remain intact |
| New-path authorization | Broker rejects protected names under directories it just created, at every tested depth |
| Broker path/type rules | Traversal, symlink parents/leaves, multiply linked files, directory replacement, special files and unknown operations fail |
| Phase policy | Read-only phases cannot put, delete or mkdir; the phase is a harness constructor input |
| Credential isolation | Synthetic file, environment, inherited descriptor and sibling-process environment access fail; host controls succeed |
| Home/config isolation | Empty synthetic home is read-only; home `.codex` creation fails |
| Network/process isolation | Host TCP and abstract Unix listeners cannot be reached; nested user namespace creation fails |
| Test execution | A fixed Python test runs; scratch writes work; arbitrary shell execution inside that test also works (negative control) |
| Timeout containment | A child that calls `setsid()` reports readiness, then stops with the PID namespace on timeout |

## Proposed trust separation

1. The existing dispatcher retains publishing credentials, lock/heartbeat/state,
   review decisions and final artifact capture. It never executes changed project
   code with these credentials. Each phase still gets a fresh worker invocation.
2. A credential-free edit broker owns a private staging tree. The broker is its
   only writer for the whole phase. The worker, tests, MCP shims and plugins must
   never have a writable mount or open write descriptor to that tree. Host paths,
   phase policy and launch settings are harness inputs, never request fields.
3. The entire Codex process belongs inside an outer filesystem/process boundary,
   with its source and instruction view read-only. Confining only shell children
   cannot cover built-in editing, hooks or MCP launched by the CLI itself.
4. The trusted Codex process uses standard authentication and credential storage.
   Verify that model-accessible tools and build/test children cannot read those
   credentials or inherit credential access. The original separate-transport
   proposal is superseded; no custom relay is planned.
5. A validated diff is imported into the real worktree by the harness. Committing,
   publishing, label transitions and staged instruction changes remain explicit
   harness operations, after their existing gates. Tests and independent reviews
   must assess the same source revision that is imported and committed.

The prototype implements a local serial broker object and disposable subprocess
sandbox, **not** the production RPC channel, source exporter, inference transport
or diff importer. The broker runs outside the sandbox in the probe. It has no
worker-accessible socket or command-line entry point in this spike.

## Edit broker assessment

A small data protocol is preferable to parsing arbitrary patches or shell
commands at the write boundary. The prototype supports `read`, `put`, `delete`
and `mkdir`, exact fields only. `put`/`delete` require the current content SHA-256;
creation requires a null expected digest. This detects stale edits. Full file
replacement is limited to 1 MiB of UTF-8 text. Binary files, multi-file atomic
transactions and directory rename/removal are unsupported in this spike.

Each operation checks every path component. Denials cover `AGENTS.md`,
`AGENTS.override.md`, `CLAUDE.md`, `CLAUDE.local.md`, `.agents`, `.codex`, `.claude`,
`.git`, `.github`, `.agent-data`, and common credential/configuration names.
Checks also reject case aliases and noncanonical paths. This deliberately narrow
Linux prototype is not a portable filename compatibility promise. A production
policy must incorporate configured instruction fallback names, memory locations,
and consumer-specific protected paths; unsupported settings must fail preflight.

Directory-descriptor traversal uses `O_NOFOLLOW` at every component. Existing
leaves must be regular files with link count one. Replacements create a new inode
and publish it atomically; they never truncate an existing hardlinked inode.
Executable mode is retained, privileged mode bits are not. No rename, link,
chmod, arbitrary command or directory replacement operation exists. Thus a worker
cannot rename a parent away to replace a protected descendant or introduce a
policy file below a newly created directory.

**Concurrency assumption matters:** directory descriptors alone do not defeat a
separate host writer moving an already-open parent. The enforcement argument
requires a private tree with exactly one serial writer, all untrusted observers
mounted read-only, and no simultaneous harness import/build modification. Do not
attach this object directly to an ordinary concurrently writable worktree. A
same-UID hostile process already outside the sandbox remains outside this threat
model; a dedicated service identity would strengthen that boundary.

Instruction reads are available through the read-only mount; the broker's generic
read operation conservatively refuses protected names. Triage plan output needs a
separate harness materialization path and schema validation; giving triage source
write permission would undo the phase policy. `CLEANUP` is conservatively read-only
in this prototype and is not a completed cleanup implementation.

## Credential and subprocess assessment

The child launcher constructs an empty environment plus fixed HOME/PATH/LANG,
closes inherited descriptors, and mounts only the host runtime `/usr` and library
aliases, the disposable source, the trusted fixture, private `/proc`, `/dev` and
scratch `/tmp`. The root and synthetic home are read-only. It creates separate
user, PID, network, IPC and other supported namespaces, drops capabilities,
disables nested user namespaces, starts a new session and uses Bubblewrap's
parent-death behavior. Source protection applies even to arbitrary code running
inside tests. Captures remain outside the mount tree.

This is a useful credential-isolation primitive, not actual worker credential
acceptance. A production source export must exclude host `.git` indirections,
ignored config, credential stores and external symlink/hardlink targets. Trusted
memory needs its own read-only snapshot. Runtime images and dependencies need an
explicit inventory; mounting this host's `/usr` is a prototype platform baseline.
Authorized source can itself contain secrets; this sandbox is not a secret
scanner. No real PAT, saved login or API key was loaded during these checks.

Authentication remains unimplemented in the worker adapter. Use standard Codex
credential loading and refresh, with tool/test isolation verified around the
trusted CLI. The earlier narrow-relay proposal was not implemented and is now out
of scope unless the operator explicitly requests it. Synthetic environment
filtering alone does not establish standard-authentication isolation.

Timeout supervision tested one detached descendant path. Normal completion,
external cancellation, parent death, broker/CLI crashes, grandchildren, and lock
release ordering still need integrated tests. Prototype file captures are bounded
when read, not while written: disk/memory/process quotas and bounded protocol
framing remain required before exposing a service to untrusted requests.

## Command restrictions and Codex attachment

The command interface accepts exactly `{"op":"test"}` and launches a fixed
harness-chosen argv in the isolated subprocess environment. It rejects shell
text, alternate argv/cwd/env/timeout, extra fields and Claude rule strings. No
string interpolation or shell-prefix interpretation occurs. The build script is
still arbitrary untrusted code: the test explicitly confirms `/bin/sh` can run
inside the sandbox. Therefore this is **tool-request restriction plus resource
isolation**, not a kernel-level executable allowlist. Allowing general builds and
claiming recursive bans on every executable would be contradictory.

For production, define named capabilities for source reads/search/diff, edits,
artifact output and harness-configured tests. Keep Git mutation and publishing in
the harness. Explicit unsupported allow/deny settings and label tool additions
must fail preflight, not silently broaden into a test/shell capability. No public
Codex tool-policy translation is introduced by this prototype.

There are two possible attachment routes:

- `codex exec` with only a harness-owned MCP shim: retains the planned JSONL CLI
  adapter, but requires proven suppression of every built-in command/edit tool,
  inherited MCP, hooks, plugins, apps and automatic discovery. MCP configuration
  alone is not a universal tool gate. The shim must not launch the privileged
  broker in the worker namespace or pass its authority to test children.
- App-server dynamic tools: the harness handles data requests directly and can
  keep broker state out of the worker. This is a promising next spike, but changes
  the proposed invocation transport and still requires built-in-tool suppression.
  Protocol control sockets must be hidden from worker/test commands, and a worker
  must not be able to override its sandbox/approval/config through that channel.

The installed CLI remains 0.153.4. Local help/features and a freshly generated
experimental app-server schema were inspected without a model call. The schema
contains `ThreadStartParams.dynamicTools`; this only establishes protocol shape.
Official [app-server documentation](https://learn.chatgpt.com/docs/app-server)
describes client-handled dynamic tool calls as experimental and documents an
external-sandbox policy for already-confined servers. Official
[rules documentation](https://learn.chatgpt.com/docs/agent-configuration/rules)
describes command approval rules separately from filesystem isolation. Neither
source establishes a complete broker-only tool surface for this installed CLI.
Do not use bypass flags or treat feature names as enforcement evidence.

[tool-probe.py](tool-probe.py) subsequently ran two actual CLI invocations with a
synthetic `offline-fixture` model/provider and a canned local Responses service.
Both the service and CLI ran inside the outer sandbox, without host network or
authentication. The service returns fixed text and synthetic usage, not inference;
that usage must never be reported as measured model usage. Both controls completed
with exactly one request. [tool-results.json](tool-results.json) records:

- The baseline request advertises `exec_command`, `write_stdin`, multi-agent
  functions, `request_user_input` and `view_image`.
- Disabling `shell_tool`, `unified_exec`, `hooks`, `plugins`, `apps`, `multi_agent`,
  browser/computer/image-generation features and `code_mode_host` leaves only
  `request_user_input` and `view_image` advertised in this fixture.

This shows progress toward a reduced tool surface, not successful hostile tool
dispatch. The fake service returns no tool calls. Model-specific tool surfaces,
undeclared calls, direct editing, inherited MCP/hook startup and unattended
approval behavior remain untested. The fixture has no project config/plugins to
exercise. A disposable writable CODEX_HOME is used only for this offline probe;
it is not the immutable configuration layout proposed for production.

## Remaining enablement gates and next experiment

1. Extend the local scripted fake model transport (no credentials or paid inference)
   to drive hostile actual Codex tool calls. Prove shell/unified execution, direct patch,
   MCP, hooks, plugins, apps, skills and approval requests cannot bypass the
   broker, including undeclared tool calls and scratch-directory config creation.
   Freeze CWD/instruction roots; writable scratch must not become a policy root.
2. Implement and test the source exporter, bounded broker protocol, phase artifact
   channel and revision-consistent importer, including interrupted transactions
   and hostile Git metadata. Freeze the test snapshot while tests run.
3. Verify standard Codex authentication with both supported modes. Keep model
   tools and build/test children isolated from the CLI's normal credential store,
   environment and descriptors. Do not implement a custom authentication relay.
4. Complete process/resource supervision and verify teardown before lock release.
   Preserve fresh independent plan/post-implementation reviews and human approval.
5. Only after required boundaries pass, implement/enable the adapter and its
   semantic event normalization. Complete portable assets and authorized isolated
   all-Codex/mixed-engine acceptance before claiming support.

The paid-run ceiling is still pending and only applies when live acceptance is
reached. These offline experiments did not need it. The selected fixture remains
`Frightful-Games/recipe-manager-demo`; access in the intended PAT context remains
to be verified. No production workers were changed.

## Validation checkpoint

All 10 broker behavior tests pass. The final host probe reports 36/36 matching
observations; both offline CLI inventory controls pass their explicit assertions.
Python syntax, local documentation links and `git diff --check` pass.
Repository prerequisites, ShellCheck and all 481 BATS tests also pass; the existing
BW01 warning in `tests/test_defaults.bats:13` remains. The full BATS log is
`/tmp/codex-broker-bats.log`. ShellCheck was extracted into `/tmp` from Ubuntu's
0.9.0 package, with the existing temporary jsonschema venv on validation PATH.
No installed runtime files were edited, and all continuation changes remain
uncommitted alongside the preserved extended native-profile evidence.

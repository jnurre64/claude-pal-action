# Extended Codex permission proof — native profile insufficient

**Historical evidence, not the current implementation roadmap.** The operator
requested native engine integration and removal of unnecessary custom complexity.
The [updated scope](../../2026-09-07-codex-worker-engine-simplicity-review.md#updated-scope-ordinary-engine-compatibility)
retires custom broker/source-staging/outer-sandbox work from the production proposal.
Results below remain observations of the tested profiles; their stronger policy
assumptions and “next steps” are superseded. Do not resume these experiments as
mandatory adapter work.

**Later operator decision:** [standard authentication and simplicity review](../../2026-09-07-codex-worker-engine-simplicity-review.md)
supersedes the separate-authentication-transport suggestion below. Keep standard
Codex authentication; no custom relay unless the operator explicitly requests it.
The recorded permission failures remain valid evidence, not a requirement to ship
every component of the proposed broker design.

Run on 2026-09-07, Codex CLI 0.153.4, on the existing Ubuntu runner host,
outside the interactive session sandbox. No model service, real credentials,
GitHub mutations, runner reconfiguration, or personal authentication changes.

The initial 18 successful checks remain valid for their tested boundaries.
**They do not establish the proposed worker policy.** This continuation records
20 boundary checks: 10 enforced the tested boundary and 10 did not. The latter
include deliberate negative controls, an unsupported policy, and successful
attacks. The adapter execution gate must remain closed.

## Reproduce

Run these commands in host context as the runner user, from this directory:

```bash
python3 probe.py > /tmp/codex-extended-proof-results.json
# Expected exit 1: required boundaries are not all enforced.
python3 config-probe.py > /tmp/codex-config-proof-results.json
# Expected exit 0: all 12 configuration observations match their controls.
```

Each invocation creates a unique disposable fixture directory. Neither script
cleans other runs or edits actual repositories/configuration. The stdout reports
are archived as [results.json](results.json) and
[config-results.json](config-results.json). Fixture paths are historical.
Both use a minimal child environment and synthetic home; the boundary probe
adds a synthetic credential canary. System managed configuration may still load.
The CLI's warning about helper aliases under `/tmp` is recorded; successful
control commands establish that it did not prevent these sandbox probes.

## Boundary observations

| Check | Observation |
| --- | --- |
| Root instruction unlink/atomic replacement, protected directory rename | Denied (`EBUSY`) |
| Create hardlink from protected mount to writable source | Denied (`EXDEV`) |
| **Write through a pre-existing hardlink alias** | **Allowed; host confirms protected `AGENTS.md` content changed** |
| Protect both hardlink paths | Alias write denied |
| Nested instruction under initial root-only policy | Write allowed |
| Explicit nested instruction read rule | Direct write denied |
| **Rename writable parent, recreate directory and instruction** | **Allowed despite exact nested instruction read rule** |
| Explicit writable parent rule plus nested read rule | Parent replacement denied (`EBUSY`) |
| Create absent instruction without a rule | Allowed |
| Exact read rule for absent instruction | Creation denied |
| Create new directory containing an instruction | Allowed |
| Recursive `read` glob | CLI refuses configuration |
| Recursive `deny` glob for existing instruction | Write denied, but this also removes required reads |
| **Recursive `deny` glob for new directory/instruction** | **Creation allowed** |
| Synthetic credential passed to `codex sandbox` | Visible to its child; filesystem rules do not sanitize environment |
| Canary removed by launcher | Absent from child environment |
| Arbitrary shell command under filesystem/network profile | Runs inside the sandbox |

The shell check is **not** an execpolicy-rule test: `codex sandbox` executes a
supplied command, not a model tool request. It establishes only that filesystem
and network profiles alone are not command allow-lists. Likewise the environment
check is not proof of `codex exec` shell-environment filtering. Real worker
credential isolation, `/proc` and inherited-descriptor paths remain unverified.

## Configuration observations and their limits

[config-probe.py](config-probe.py) always supplies a nonexistent model provider,
no authentication, and no executable hook. This forces a startup error before
model execution. Its MCP checks only list configuration; the configured server
executables do not exist and are never launched.

- `--ignore-user-config` bypasses malformed synthetic user configuration.
  Without it, parsing fails, validating the control.
- Trusted malformed project configuration fails without that flag, but with it
  execution reaches the deliberate missing-provider error. This is evidence for
  **this startup/configuration path**, not a general guarantee that every project
  instruction, plugin, hook, or later config loader is suppressed.
- Invalid project approval configuration is detected in the trusted control.
  The explicit approval override case reaches the missing-provider error but
  does not prove effective unattended approval behavior during a tool request.
- In `codex mcp list`, `-c 'mcp_servers={}'` leaves both synthetic user and project
  servers enabled. Disabling each server by its explicit name works. Do not use
  an empty-table override as proof that inherited MCP is disabled in `exec`.
- Hook/plugin execution, MCP startup/calls, managed requirements, and model-driven
  command/approval paths are still untested. These 12 passing **observations**
  must not be described as 12 passing isolation boundaries.

## Implementation consequence

The simple native implementation profile cannot yet meet the approved policy.
Exact parent rules repair the observed rename path, and rejecting multiply linked
protected files would avoid the demonstrated pre-existing alias. Neither solves
policy creation under new writable directories. A one-time scan or a post-run
diff check is not enforcement during a worker session.

Before enabling a write-capable adapter, prove an external enforcement layer or
a mediated mutation path. A concrete candidate for the next implementation spike:

1. Mount the worker's source and instructions read-only and deny access to the
   runner home, publishing credentials, sibling processes and capture artifacts.
   Use standard authentication in the trusted Codex process and isolate its
   credentials from model-accessible tools and test children. Define and test
   filesystem, process and network isolation together.
2. Route edits through a harness-owned broker which rejects instruction/config
   basenames and directories at every depth, symlink traversal, hardlinks and
   parent replacement. Authorize destinations immediately before each mutation;
   never rely only on the paths present at dispatch start. The worker cannot
   modify the broker, its policy, or its launch environment.
3. Expose only that vetted broker/tool set to Codex. Test actual shell, direct
   editing, MCP, hook and plugin paths; explicitly reject unsupported configured
   tool rules. Build/test subprocesses must receive neither publishing nor model
   credentials. Review phases retain read-only source throughout.
4. Verify cancellation of the broker/CLI/descendants before lock release. Then
   implement and test the invocation adapter, JSONL normalizer and authentication
   modes, followed by the previously planned live acceptance.

This is a candidate design, not a shipped policy or a claim that an external
sandbox is already installed. Read-only Codex review support could be developed
separately, but it would not fulfill the approved all-phase/all-Codex scope.
Do not silently substitute that reduced release for issue #116.

Official references checked alongside the executable observations:
[permission profiles](https://learn.chatgpt.com/docs/permissions) document
read/deny path controls and limitations on portable read globs;
[configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference)
describes shell environment and per-server MCP settings;
[rules](https://learn.chatgpt.com/docs/agent-configuration/rules) describe command
policy separately from sandbox filesystem permissions. The recorded probe
results, rather than documentation alone, support the observed failure claims.

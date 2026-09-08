# Native instruction prevention: decision checkpoint

Checked 2026-09-07. Installed CLIs remain Codex 0.153.4 and Claude Code 2.1.263.
The cross-engine prevention requirement is **not met**. No runtime policy was
changed and Codex remains disabled. Repeating the earlier Codex probe is not
necessary: the version is unchanged and its archived failures remain applicable.

## What is established

- Codex's prior host observations show protected content changed through a
  pre-existing hardlink, nested parent replacement, and instruction creation in a
  new directory. Exact-path repairs cover only some cases. Current
  [Codex permissions documentation](https://learn.chatgpt.com/docs/permissions)
  still describes Linux deny-read glob expansion before sandbox startup; it does
  not establish a dynamic instruction-basename write prohibition. See the
  [earlier executable evidence](../2026-09-07-codex-sandbox-extended/README.md).
- Claude's [permission documentation](https://code.claude.com/docs/en/permissions)
  explicitly distinguishes Edit deny rules from arbitrary Python/Node subprocess
  file access. Tool deny patterns alone do not implement the required boundary.
  The [sandbox documentation](https://code.claude.com/docs/en/sandboxing) describes
  filesystem protection for Bash subprocesses, separately from built-in tools.
  This repository's Claude adapter does not require that sandbox or inject
  instruction denies; its defaults cannot be represented as enforcing the new rule.
- The published [Anthropic sandbox runtime](https://github.com/anthropics/sandbox-runtime)
  documents literal Linux paths, with glob support on macOS. Its published Linux
  implementation resolves deny paths and assembles bind mounts before launching a
  command. This is not evidence of dynamic protection for arbitrary new filenames.
  A startup scan cannot close creation within a running command.

## New no-model component probe

Installed `@anthropic-ai/sandbox-runtime@0.0.75` only under `/tmp/sp116-native-srt`,
with npm lifecycle scripts disabled. [package-lock.json](package-lock.json) pins
the package, dependencies and integrity hashes. The first install encountered an
older npm date cutoff; the successful command explicitly used `--before=2026-09-08`.
No global package, installed Claude binary, login or host profile was changed.

[probe.py](probe.py) creates isolated temporary workspaces and synthetic homes.
It passes explicit literal denies for root `AGENTS.md` and nested `Claude.md`.
Ten cases cover ordinary source edits/new directories, instruction reads, direct
writes, symlink/hardlink writes, unlink, parent replacement and new `Agents.md`.
It inherits no credential variables, makes no model calls and configures no
allowed network domains. Research access is not tested by this fixture.

All ten [unconfined controls](baseline.json) execute successfully, confirming
that the intended operations work in the disposable fixture. All ten confined
cases in [results.json](results.json) fail **before the test command starts**:

```text
apply-seccomp: write /proc/self/setgroups (nested userns is capability-restricted; caller must provide CAP_SYS_ADMIN): Permission denied
```

The final probe exits **2**, meaning unavailable enforcement, not ten denied
attacks. No capability grant or weaker sandbox option was tried. This separately
installed component is not proven to match the version bundled into Claude Code;
its startup error does not establish a Claude Code startup failure. Actual Claude
built-in-tool and sandbox alias/replacement enforcement remains unverified.

Reproduce in host context as the ordinary runner user:

```bash
python3 probe.py /tmp/sp116-native-srt/node_modules/.bin/srt --baseline
python3 probe.py /tmp/sp116-native-srt/node_modules/.bin/srt
```

Exit 0 means the fixture expectations matched; 1 means an observed mismatch;
2 means at least one test command could not run. Each child has a 20-second
timeout and process-group cleanup. This is evidence tooling, not an installed
worker wrapper or release gate. Do not run it as root.

## Decision and smallest additional option

There is no verified stock configuration satisfying the complete requirement on
this Linux host while allowing arbitrary source editing and test subprocesses.
Adding Edit denies or enumerating current files would be partial hardening, not
completion. A post-run diff/revert gate would protect publication only and would
change the operator's prevention requirement. Do not silently substitute it.

The smallest native change to investigate upstream is runtime-enforced filename
protection covering new entries, aliases and directory operations across editing
tools and subprocesses. No such supported setting was established in this audit.
Until one is verified, preserve the closed Codex release gate and continue the
independent workflow/delivery work. Stop treating another unchanged native-profile
probe as a likely implementation milestone.

The only concrete local enforcement candidate already prepared is the
[parked AppArmor experiment](../2026-09-07-instruction-apparmor/README.md).
It is unverified for aliases and native sandbox compatibility and is **not** a
known working solution. Its load request remains withdrawn. Reopening it would
require an explicit new scope decision; this checkpoint does not request a load,
revive a broker, or change the strict prevention requirement. A review-only Codex
release would likewise require a separate scope decision and would not complete
the approved all-phase integration.

Validation: all ten baseline controls pass; confined startup refusal is recorded
as unavailable. Python syntax, report consistency, local links and whitespace
checks pass. Runtime files are unchanged, so the 520 passing BATS tests and
ShellCheck result from the configuration milestone remain historical validation.

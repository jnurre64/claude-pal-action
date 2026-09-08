# Small AppArmor instruction-policy experiment

**Parked: the operator asked to move on from custom OS enforcement. The load
request is withdrawn; do not execute the historical load commands below.**
No experimental profile has been loaded by this session.

Historical status: prepared and compiled; kernel enforcement was not tested.
Codex remains disabled. No worker adapter, authentication, runner service, system
profile or production repository was changed by this experiment.

## What is being evaluated

Can a small process policy prevent AGENTS.md/CLAUDE.md edits while retaining
ordinary editing, descendant commands and research? AppArmor is installed on this
Ubuntu host (parser 4.0.1). It is a standard OS facility; the proposed profile is
project-specific configuration, not stock Claude/Codex behavior or a portable
solution. It is not another edit broker or authentication service.

The [template](profile.in) defines no executable attachment. It is selected only
by an explicit `aa-exec -p <name>` for fixture children. Inherited execution keeps
the selected profile on ordinary descendants. Filename denies cover case variants
at any depth, including new files. Exact denies pin the disposable fixture's known
protected parent directories. Ordinary child-file writes are tested separately.

Two profiles share these file rules:

- `strict`: no capabilities, mount or user-namespace grants.
- `native`: allows those operations to test native sandbox compatibility and
  whether mount aliases bypass the filename rules. Those broad grants make this
  an experimental comparison, **not a recommended production profile**.

The profiles deliberately allow general file/network operations otherwise. Existing
engine controls would still be needed in a real integration. They do not provide
credential isolation, domain filtering, or a complete worker security policy.

AppArmor documents link-creation permission-subset checks and separate directory
write permissions. A pre-existing hardlink is a different case: matching only the
protected filename must not be assumed to protect its other inode aliases. The
probe retains that attack and an explicit mount-alias attack as required-denial
cases, not exclusions that turn a failing candidate green.
[Profile syntax](https://manpages.debian.org/bookworm/apparmor/apparmor.d.5.en.html).

## Completed checks

The current prepared fixture is `/tmp/sp116-apparmor-zo7gjn9f`. Its generated
[profile copy](prepared-profiles.txt) is archived for review; the paths and names
are specific to this fixture. `apparmor_parser -Q -K` successfully compiled it
without loading policy or writing system caches. `apparmor_parser -N -K` lists
exactly these names:

```text
sp116-apparmor-zo7gjn9f-strict
sp116-apparmor-zo7gjn9f-native
```

All 21 [unconfined controls](baseline.json) pass, including protected-file attacks,
ordinary edits/renames, a shell child, localhost TCP connectivity, both CLI version
commands, Codex's no-model sandbox startup, and a writable mount alias. These are
positive controls for the fixture, **not 21 passing protection checks**. Local TCP
connectivity is a research-access smoke test, not a live web-tool acceptance run.
CLI version commands do not prove complete Claude/Codex session compatibility.

The [unloaded-profile check](pending.json) exits 2 with `profile_unavailable`.
The runner refuses to interpret failure to start `aa-exec` as successful enforcement.
The host shell is unconfined; reading the loaded-profile list requires privilege,
and `sudo -n true` reports that a password is required. No policy load was attempted.
No automatic approval rejection occurred.

## Historical privileged steps — withdrawn, do not run

Kernel enforcement requires loading policy; offline compilation cannot establish
it. [Kernel AppArmor documentation](https://docs.kernel.org/admin-guide/LSM/apparmor.html).
After reviewing the generated profile, the operator can load these two temporary,
unattached profiles with:

```bash
sudo apparmor_parser -a -K /tmp/sp116-apparmor-zo7gjn9f/profiles
```

This uses add, not replace; an existing name causes a failure. It changes the
kernel's profile registry, but does not edit `/etc/apparmor.d`, change the existing
Bubblewrap profile, attach policy to running services, or persist across reboot.
The session cannot supply the required sudo password. **Do not run the Python
probe as root.** After loading, run in host context as the normal user:

```bash
python3 docs/superpowers/plans/evidence/2026-09-07-instruction-apparmor/probe.py run \
  /tmp/sp116-apparmor-zo7gjn9f > /tmp/sp116-apparmor-zo7gjn9f/results.json
```

The probe uses only disposable files, a synthetic home, a local listener and
scripted commands. No authentication or model calls are involved. Each child has
a 20-second deadline and process-group cleanup. Inspect every failed observation;
exit 1 means at least one requirement failed, and exit 2 means enforcement could
not be tested. Exit 0 is only success for these fixtures, not production approval.

Unload the temporary profiles after testing (also if a test fails):

```bash
sudo apparmor_parser -R -K /tmp/sp116-apparmor-zo7gjn9f/profiles
```

Keep the fixture directory until the profiles have been unloaded. The normal
orchestrator/test parent remains outside the profile and can reset only its
disposable workspace between completed children; that is not a production import
mechanism. Never select these experimental profiles for real workers.

## Reproduction and next decision

`python3 probe.py prepare` creates a fresh fixture and compiles fresh names/paths;
use the printed directory in subsequent commands. `python3 probe.py baseline DIR`
runs the unconfined controls. The tool contains no sudo, policy-loading or host
configuration commands. In an interactive sandbox, these host controls need a
host-context tool invocation; nested interactive confinement is not the baseline.

Only after kernel results are available, decide whether this is a small viable
addition. Do not quietly accept hardlink/mount bypasses, weaken the user's file
protection requirement, or restart the retired broker architecture. Actual engine
tool calls, configuration inheritance, lifecycle coverage, more alias variants and
research tools still require acceptance even if these initial fixtures pass.

Evidence-only validation: compilation, positive controls, unloaded-profile refusal,
Python syntax, local links and `git diff --check`. The preceding runtime milestone
had 490 passing BATS tests; they were not rerun for this evidence-only change.

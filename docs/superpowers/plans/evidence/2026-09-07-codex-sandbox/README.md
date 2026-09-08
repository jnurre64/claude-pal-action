# Initial Codex sandbox evidence

Captured on 2026-09-07 with Codex CLI 0.153.4 on the Ubuntu 24.04 runner host,
after the operator installed and loaded Ubuntu's standard
`bwrap-userns-restrict` AppArmor profile. All 18 checks passed.

- [probe.py](probe.py): exact no-model probe used in this session.
- [results.json](results.json): recorded results; fixture paths refer to temporary
  directories from that run and may no longer exist.

To repeat, run `python3 probe.py` in the host context as the runner user.
Requires Codex, Python 3 at `/usr/bin/python3`, and working sandbox prerequisites.
The probe creates disposable fixtures under `/tmp`, overwrites
`/tmp/codex-runner-boundary-results.json`, and leaves fixtures for inspection.
It starts a local-only listener and uses synthetic credentials; it makes no model
calls or GitHub changes. Do not run concurrent copies because the result path is
shared. An outer sandbox can affect results, so use the host context for host
verification.

These are command-boundary observations, not a complete worker permission proof.
The profiles are supplied only for these fixtures and are not installed worker
policies. See the [handoff](../../2026-09-07-codex-worker-engine-handoff.md) for
remaining command, MCP, credential, configuration, and process-isolation work.

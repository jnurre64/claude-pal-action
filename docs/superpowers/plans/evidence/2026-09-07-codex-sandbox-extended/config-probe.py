#!/usr/bin/env python3
"""No-model config-layer probes, with an unresolvable model provider.

User/project configuration is synthetic; system managed layers may still load.
No authentication is supplied, no MCP server is started, and no hook commands
are configured.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


root = Path(tempfile.mkdtemp(prefix="codex-config-proof-"))
home = root / "home"
work = root / "workspace"
(home / ".codex").mkdir(parents=True)
(work / ".codex").mkdir(parents=True)
(work / ".git").mkdir()
env = {"HOME": str(home), "PATH": os.environ["PATH"]}
codex = shutil.which("codex")
results = []


def probe(name, user_config, project_config, *, ignore=True, overrides=(),
          expected="Model provider `sp-proof-missing-provider` not found"):
    (home / ".codex/config.toml").write_text(user_config)
    (work / ".codex/config.toml").write_text(project_config)
    # Missing provider is a deliberate, deterministic startup stop. This
    # command must never be repurposed to use a real provider or credentials.
    args = [codex, "exec", "--ephemeral", "--ignore-rules", "--skip-git-repo-check",
            "-C", str(work), "-c", 'model_provider="sp-proof-missing-provider"',
            "-c", 'projects.' + json.dumps(str(work)) + '.trust_level="trusted"']
    if ignore:
        args.append("--ignore-user-config")
    for value in overrides:
        args.extend(["-c", value])
    cp = subprocess.run(args + ["-"], input="No model call is permitted.",
                        env=env, capture_output=True, text=True, timeout=15)
    results.append(dict(name=name, exit_code=cp.returncode,
                        observation_verified=cp.returncode != 0 and expected in cp.stderr,
                        diagnostic=(cp.stderr + cp.stdout)[-4000:]))


probe("ignored malformed user config", "invalid = [", "")
probe("malformed user config control", "invalid = [", "", ignore=False, expected="unclosed array")
probe("project config despite ignore-user-config", "", 'approval_policy="sp-proof-invalid"')
probe("explicit approval overrides project value", "", 'approval_policy="sp-proof-invalid"',
      overrides=('approval_policy="never"',))
probe("malformed project config despite ignore-user-config", "", "invalid = [")
trust = '[projects.' + json.dumps(str(work)) + ']\ntrust_level="trusted"\n'
probe("trusted malformed project control", trust, "invalid = [", ignore=False, expected="Error parsing project config file")
probe("trusted malformed project with ignore-user-config", trust, "invalid = [")
probe("trusted project invalid approval control", trust, 'approval_policy="sp-proof-invalid"',
      ignore=False, expected="unknown variant `sp-proof-invalid`")

# Listing configuration does not initialize or call these nonexistent servers.
(home / ".codex/config.toml").write_text(
    '[mcp_servers.synthetic_user]\ncommand="/sp-proof-never-execute"\n'
    '[projects.' + json.dumps(str(work)) + ']\ntrust_level="trusted"\n')
(work / ".codex/config.toml").write_text(
    '[mcp_servers.synthetic_project]\ncommand="/sp-proof-never-execute"\n')
for override in (None, "mcp_servers={}", "mcp_servers.synthetic_user.enabled=false",
                 "mcp_servers.synthetic_project.enabled=false"):
    args = [codex, "mcp", "list", "--json"]
    if override:
        args += ["-c", override]
    cp = subprocess.run(args, env=env, cwd=work, capture_output=True, text=True, timeout=15)
    try:
        servers = {item["name"]: item["enabled"] for item in json.loads(cp.stdout)}
    except (ValueError, KeyError, TypeError):
        servers = {}
    expected_servers = {"synthetic_user": override != "mcp_servers.synthetic_user.enabled=false",
                        "synthetic_project": override != "mcp_servers.synthetic_project.enabled=false"}
    results.append(dict(name="MCP config listing: " + str(override), exit_code=cp.returncode,
                        observation_verified=cp.returncode == 0 and servers == expected_servers,
                        output=cp.stdout, diagnostic=cp.stderr[-1000:]))

print(json.dumps(dict(fixture_root=str(root), results=results), indent=2))
raise SystemExit(0 if all(item["observation_verified"] for item in results) else 1)

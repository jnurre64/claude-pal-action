#!/usr/bin/env python3
"""No-model policy observations. Only disposable paths and synthetic secrets.

Run in host context; stdout is a JSON report. A successful observation is not
necessarily a secure boundary: inspect `boundary_enforced` for every case.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


def main():
    root = Path(tempfile.mkdtemp(prefix="codex-extended-proof-"))
    codex = shutil.which("codex")
    if not codex:
        raise SystemExit("codex is required")
    results = []
    # Deliberately exclude the operator's credential environment. The canary
    # tests the same inheritance path without disclosing any actual secrets.
    env = {"PATH": os.environ["PATH"], "HOME": str(root / "home"),
           "SP_PROOF_CREDENTIAL": "synthetic-proof-only"}
    (root / "home").mkdir()

    def run(name, operation, *, extra=None, must_deny=True, setup=None,
            clean_environment=False):
        work = root / str(len(results)) / "workspace"
        work.mkdir(parents=True)
        for relative in ("AGENTS.md", "CLAUDE.md", ".agents/policy", ".codex/policy",
                         ".claude/policy", "src/AGENTS.md", "src/code.py"):
            p = work / relative
            p.parent.mkdir(exist_ok=True)
            p.write_text("original")
        (work / "replacement").write_text("replacement")
        if setup:
            setup(work)
        paths = {".": "write", "AGENTS.md": "read", "CLAUDE.md": "read",
                 ".agents": "read", ".codex": "read", ".claude": "read"}
        paths.update(extra or {})
        settings = ('permissions.sp-proof={filesystem={":root"="read", '
                    '":workspace_roots"={' + ",".join(
                        json.dumps(k) + "=" + json.dumps(v) for k, v in paths.items())
                    + '}},network={enabled=false}}')
        code = """import errno, json, os
from pathlib import Path
try:
    exec(OPERATION)
except OSError as e:
    print(json.dumps({'denied': e.errno in (errno.EACCES, errno.EPERM, errno.EROFS, errno.EBUSY, errno.EXDEV), 'errno': e.errno}))
else:
    print(json.dumps({'denied': False}))
""".replace("OPERATION", repr(operation))
        child_env = dict(env)
        if clean_environment:
            child_env.pop("SP_PROOF_CREDENTIAL")
        cp = subprocess.run([codex, "sandbox", "-P", "sp-proof", "-C", str(work),
                             "-c", settings, "/usr/bin/python3", "-c", code],
                            env=child_env, capture_output=True, text=True, timeout=20)
        try:
            observed = json.loads(cp.stdout)
        except ValueError:
            observed = {}
        results.append(dict(name=name, process_exit_code=cp.returncode,
                            observation=observed,
                            root_instruction_unchanged=(work / 'AGENTS.md').read_text() == 'original',
                            nested_instruction_unchanged=(work / 'src/AGENTS.md').exists() and
                            (work / 'src/AGENTS.md').read_text() == 'original',
                            boundary_enforced=(cp.returncode == 0 and
                                               observed.get("denied") == must_deny)))
        if cp.returncode:
            results[-1]["diagnostic"] = cp.stderr[-1000:]

    run("root instruction unlink", "Path('AGENTS.md').unlink()")
    run("root instruction atomic replacement", "os.replace('replacement', 'AGENTS.md')")
    run("protected directory rename", "os.rename('.codex', 'moved')")
    run("hardlink protected inode into writable source", "os.link('AGENTS.md', 'alias'); Path('alias').write_text('changed')")
    run("pre-existing hardlink alias to protected instruction", "Path('alias').write_text('changed')",
        setup=lambda work: os.link(work / 'AGENTS.md', work / 'alias'))
    run("pre-existing hardlink with both paths protected", "Path('alias').write_text('changed')",
        setup=lambda work: os.link(work / 'AGENTS.md', work / 'alias'), extra={"alias": "read"})
    run("nested instruction with root-only policy", "Path('src/AGENTS.md').write_text('changed')")
    run("nested instruction with exact policy", "Path('src/AGENTS.md').write_text('changed')",
        extra={"src/AGENTS.md": "read"})
    run("nested parent replacement with exact policy", "os.rename('src', 'moved')",
        extra={"src/AGENTS.md": "read"})
    run("nested parent rename and instruction replacement",
        "os.rename('src', 'moved'); Path('src').mkdir(); Path('src/AGENTS.md').write_text('changed')",
        extra={"src/AGENTS.md": "read"})
    run("explicit writable parent mount replacement",
        "os.rename('src', 'moved'); Path('src').mkdir(); Path('src/AGENTS.md').write_text('changed')",
        extra={"src": "write", "src/AGENTS.md": "read"})
    run("absent nested instruction creation", "Path('src/CLAUDE.md').write_text('changed')")
    run("absent nested instruction exact policy", "Path('src/CLAUDE.md').write_text('changed')",
        extra={"src/CLAUDE.md": "read"})
    run("new directory instruction creation", "Path('new').mkdir(); Path('new/AGENTS.md').write_text('changed')")
    run("nested read glob", "Path('src/AGENTS.md').write_text('changed')",
        extra={"**/AGENTS.md": "read"})
    run("deny glob existing instruction write", "Path('src/AGENTS.md').write_text('changed')",
        extra={"**/AGENTS.md": "deny"})
    run("deny glob new directory instruction creation",
        "Path('new').mkdir(); Path('new/AGENTS.md').write_text('changed')",
        extra={"**/AGENTS.md": "deny"})
    run("credential environment inheritance", "assert os.environ.get('SP_PROOF_CREDENTIAL') != 'synthetic-proof-only'",
        must_deny=False)
    run("credential removed by launcher", "assert 'SP_PROOF_CREDENTIAL' not in os.environ",
        must_deny=False, clean_environment=True)
    run("arbitrary command in filesystem sandbox", "import subprocess; subprocess.run(['/bin/sh', '-c', 'echo executed > arbitrary-command'], check=True)")
    report = dict(cli_version=subprocess.check_output([codex, "--version"], env=env, text=True).strip(),
                  fixture_root=str(root), results=results)
    print(json.dumps(report, indent=2))
    # Boundary failures are evidence, never quietly reclassified as passes.
    return 0 if all(item["boundary_enforced"] for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())

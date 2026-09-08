#!/usr/bin/env python3
"""Prepare/execute no-model fixtures. Never loads policy or invokes sudo.

Preparation and baseline need no policy change. The run command requires the
reviewed named profiles to have been loaded separately by an administrator.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import signal
import socket
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent


def prepare():
    root = Path(tempfile.mkdtemp(prefix="sp116-apparmor-"))
    name = root.name
    for part in ("workspace/src", "home/.codex", "tmp"):
        (root / part).mkdir(parents=True)
    profiles = []
    for variant, rules in (("strict", "# No mount, capability or userns grants."),
                           ("native", "capability, userns, mount, umount, pivot_root,")):
        profiles.append((HERE / "profile.in").read_text().replace("@NAME@", name + "-" + variant)
                        .replace("@ROOT@", str(root)).replace("@NAMESPACE_RULES@", rules))
    (root / "profiles").write_text('abi <abi/4.0>,\n' + "\n".join(profiles))
    (root / "manifest.json").write_text(json.dumps({"root": str(root), "profile_prefix": name}))
    subprocess.run(["apparmor_parser", "-Q", "-K", str(root / "profiles")], check=True)
    reset(root)
    print(root)


def reset(root):
    # Delete only this prepared fixture's workspace, never a repository tree.
    work = root / "workspace"
    if work.exists():
        shutil.rmtree(work)
    (work / "src").mkdir(parents=True)
    for rel in ("AGENTS.md", "CLAUDE.md", "src/AGENTS.md"):
        (work / rel).write_text("original\n")
    (work / "src/code.txt").write_text("code\n")
    (work / "replacement").write_text("replacement\n")


def root_from(value):
    root = Path(value).resolve()
    if root.parent != Path("/tmp") or not re.fullmatch(r"sp116-apparmor-[a-z0-9_]+", root.name):
        raise ValueError("Expected a prepared /tmp/sp116-apparmor-* fixture")
    if root.is_symlink() or root.stat().st_uid != os.getuid():
        raise ValueError("Fixture must be owned by the invoking user")
    data = json.loads((root / "manifest.json").read_text())
    if data != {"root": str(root), "profile_prefix": root.name}:
        raise ValueError("Invalid fixture manifest")
    return root


def invoke(root, profile, command):
    env = {"PATH": os.environ["PATH"], "HOME": str(root / "home"),
           "CODEX_HOME": str(root / "home/.codex"), "TMPDIR": str(root / "tmp"),
           "LANG": "C.UTF-8"}
    argv = (["aa-exec", "-p", profile, "--"] if profile else []) + command
    process = subprocess.Popen(argv, cwd=root / "workspace", env=env,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True, start_new_session=True)
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=20)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(process.pid, signal.SIGKILL)
        stdout, stderr = process.communicate()
    finally:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    return {"exit_code": process.returncode, "stdout": stdout[-4000:],
            "stderr": stderr[-2000:], "timed_out": timed_out}


def protected_snapshot(work):
    return {str(p.relative_to(work)): p.read_text() for p in work.rglob("*")
            if p.is_file() and p.name.lower() in ("agents.md", "claude.md")}


def run(root, baseline):
    if os.geteuid() == 0:
        raise ValueError("Run fixtures as the normal user, never with sudo")
    profiles = [None] if baseline else [root.name + "-strict", root.name + "-native"]
    results = []
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen(64)
        port = listener.getsockname()[1]
        cases = [
            ("instruction read", "assert Path('AGENTS.md').read_text() == 'original\\n'", False),
            ("ordinary source edit", "Path('src/code.txt').write_text('edited')", False),
            ("ordinary directory creation", "Path('new').mkdir(); Path('new/code').write_text('ok')", False),
            ("ordinary source rename", "os.rename('src/code.txt', 'src/renamed.txt')", False),
            ("descendant source edit", "Path('src/code.txt').write_text('edited')", False),
            ("research connection", f"import socket; socket.create_connection(('127.0.0.1', {port}), timeout=2).close()", False),
            ("direct protected write", "Path('AGENTS.md').write_text('changed')", True),
            ("descendant protected write", "Path('CLAUDE.md').write_text('changed')", True),
            ("nested protected write", "Path('src/AGENTS.md').write_text('changed')", True),
            ("protected unlink", "Path('CLAUDE.md').unlink()", True),
            ("atomic replacement", "os.replace('replacement', 'AGENTS.md')", True),
            ("protected parent replacement", "os.rename('src', 'moved'); Path('src').mkdir(); Path('src/AGENTS.md').write_text('changed')", True),
            ("new nested instruction", "Path('new').mkdir(); Path('new/Agents.md').write_text('changed')", True),
            ("symlink alias", "Path('alias').symlink_to('AGENTS.md'); Path('alias').write_text('changed')", True),
            ("new hardlink alias", "os.link('AGENTS.md', 'alias'); Path('alias').write_text('changed')", True),
            ("pre-existing hardlink alias", "Path('alias').write_text('changed')", True),
            ("renaming ordinary file to instruction", "os.rename('src/code.txt', 'src/Claude.md')", True),
        ]
        for profile in profiles:
            # Refuse to score policy denial if aa-exec itself could not start.
            startup = invoke(root, profile, ["/usr/bin/python3", "-c",
                "from pathlib import Path; print(Path('/proc/self/attr/current').read_text().strip())"])
            if startup["exit_code"] or (profile and startup["stdout"].strip() != profile + " (enforce)"):
                print(json.dumps({"state": "profile_unavailable", "profile": profile, "startup": startup}, indent=2))
                return 2
            for name, operation, must_deny in cases:
                reset(root)
                work = root / "workspace"
                if name == "pre-existing hardlink alias":
                    os.link(work / "AGENTS.md", work / "alias")
                before = protected_snapshot(work)
                script = "import os,json,errno\nfrom pathlib import Path\ntry:\n    exec(" + repr(operation) + ")\nexcept OSError as exc:\n    print(json.dumps({'denied':exc.errno in [errno.EACCES,errno.EPERM,errno.EROFS,errno.EBUSY,errno.EXDEV], 'errno':exc.errno}))\nelse:\n    print(json.dumps({'denied':False}))\n"
                command = ["/usr/bin/python3", "-c", script]
                if name.startswith("descendant "):
                    command = ["/bin/sh", "-c", '"$@"', "fixture-shell"] + command
                observed = invoke(root, profile, command)
                try:
                    observation = json.loads(observed["stdout"])
                except ValueError:
                    observation = {}
                unchanged = before == protected_snapshot(work)
                expected_deny = must_deny and not baseline
                results.append({"profile": profile, "case": name, **observed,
                    "instruction_unchanged": unchanged, "observation": observation,
                    "matches_requirement": observed["exit_code"] == 0 and observation.get("denied") == expected_deny
                        and (not expected_deny or unchanged)})

            for engine in ("claude", "codex"):
                binary = shutil.which(engine)
                observed = invoke(root, profile, [binary, "--version"]) if binary else {"exit_code": 127}
                results.append({"profile": profile, "case": engine + " startup", **observed,
                                "matches_requirement": observed["exit_code"] == 0})
            reset(root)
            codex = shutil.which("codex")
            if codex:
                observed = invoke(root, profile, [codex, "sandbox", "-P", ":read-only", "-C", str(root / "workspace"), "/bin/echo", "native-sandbox-started"])
                results.append({"profile": profile, "case": "native Codex sandbox startup", **observed,
                                "matches_requirement": observed["exit_code"] == 0 and "native-sandbox-started" in observed["stdout"]})
            # Alias the protected inode under an ordinary basename in a new mount
            # namespace. Broad namespace permissions must not silently bypass rules.
            reset(root)
            work = root / "workspace"
            (work / "alias").touch()
            observed = invoke(root, profile, ["/usr/bin/bwrap", "--die-with-parent", "--unshare-user",
                "--bind", "/", "/", "--bind", str(work / "AGENTS.md"), str(work / "alias"),
                "/usr/bin/python3", "-c", "from pathlib import Path; Path('alias').write_text('changed')"])
            unchanged = (work / "AGENTS.md").read_text() == "original\n"
            results.append({"profile": profile, "case": "mount alias", **observed,
                            "instruction_unchanged": unchanged,
                            "matches_requirement": (observed["exit_code"] == 0 and not unchanged) if baseline
                                else (observed["exit_code"] != 0 and unchanged and not observed["timed_out"])})
    report = {"baseline": baseline, "root": str(root), "results": results,
              "all_requirements_pass": all(r["matches_requirement"] for r in results)}
    print(json.dumps(report, indent=2))
    return 0 if report["all_requirements_pass"] else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["prepare", "baseline", "run"])
    parser.add_argument("root", nargs="?")
    args = parser.parse_args()
    if args.mode == "prepare":
        prepare()
    else:
        raise SystemExit(run(root_from(args.root), args.mode == "baseline"))

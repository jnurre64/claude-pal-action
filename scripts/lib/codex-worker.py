#!/usr/bin/env python3
"""Native Codex transport for the shared worker interface.

Native settings are supplied by the phase-policy adapter. This module does
not translate Claude tool rules or claim instruction-file/credential isolation.
"""
import json
import os
from pathlib import Path
import runpy
import signal
import stat
import subprocess
import sys
import tempfile
import uuid

RESULT = runpy.run_path(str(Path(__file__).with_name("agent-result.py")))


def preflight():
    try:
        help_result = subprocess.run(["codex", "exec", "--help"], capture_output=True,
                                     text=True, timeout=15)
        required = ("--json", "--output-last-message", "--output-schema", "--sandbox", "--ephemeral")
        if help_result.returncode or any(flag not in help_result.stdout for flag in required):
            return "Installed Codex CLI lacks required exec capabilities"
        # CODEX_API_KEY is the documented exec-only API-key override. Otherwise
        # let Codex inspect its normal credential store; never open/copy it here.
        if not os.environ.get("CODEX_API_KEY"):
            auth = subprocess.run(["codex", "login", "status"], stdout=subprocess.DEVNULL,
                                  stderr=subprocess.DEVNULL, timeout=15)
            if auth.returncode:
                return "Codex authentication is unavailable; use codex login or CODEX_API_KEY"
    except (OSError, subprocess.TimeoutExpired):
        return "Codex CLI is unavailable or its preflight timed out"
    return None


def failure(phase, message):
    result = RESULT["normalize_codex"]("", phase, 127, "", None, "configuration")
    result["process_exit_code"] = None
    result["error"] = {"kind": "configuration", "message": message}
    return result


def validate(request):
    if not isinstance(request, dict):
        raise ValueError("Expected worker request object")
    if set(request) - {"phase", "sandbox", "timeout", "prompt", "model", "schema_json",
                       "worktree", "capture_root", "persist", "effort", "add_dirs"}:
        raise ValueError("Unsupported worker request setting")
    phase = request.get("phase")
    if phase not in ("TRIAGE", "REPLY", "VALIDATE", "IMPLEMENT", "REVIEW", "ADVERSARIAL_PLAN",
                     "POST_IMPL_REVIEW", "POST_IMPL_RETRY", "TEST_FIX", "CLEANUP"):
        raise ValueError("Unknown worker phase")
    if request.get("sandbox") not in ("read-only", "workspace-write"):
        raise ValueError("An explicit supported native sandbox is required")
    if type(request.get("timeout")) is not int or request["timeout"] <= 0:
        raise ValueError("Worker timeout must be a positive integer")
    for key in ("prompt", "model", "schema_json", "worktree", "capture_root"):
        if not isinstance(request.get(key), str):
            raise ValueError("Missing worker text/path field")
    if type(request.get("persist", False)) is not bool:
        raise ValueError("Persistence must be boolean")
    if request.get("effort", "") not in ("", "minimal", "low", "medium", "high", "xhigh"):
        raise ValueError("Unsupported native Codex effort")
    if not isinstance(request.get("add_dirs", []), list) or any(
            not isinstance(path, str) or not Path(path).is_absolute() for path in request.get("add_dirs", [])):
        raise ValueError("Additional writable directories must be absolute paths")
    worktree = Path(request["worktree"]).resolve(strict=True)
    capture_root = Path(request["capture_root"]).resolve(strict=True)
    if not worktree.is_dir() or not capture_root.is_dir() or capture_root.is_relative_to(worktree):
        raise ValueError("Capture root must be an existing directory outside the worktree")
    if request["schema_json"]:
        RESULT["validator_for"](RESULT["loads"](request["schema_json"]))
    return worktree, capture_root


def read_final(path):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, encoding="utf-8") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                return None
            return stream.read()
    except (OSError, UnicodeError):
        return None


def phase_schema(phase, schema_text):
    if phase != "TRIAGE":
        return schema_text
    schema = RESULT["loads"](schema_text) if schema_text else {
        "type": "object", "properties": {"action": {"type": "string", "enum": ["ask_questions", "plan_ready"]}}, "required": ["action"]}
    # Keep local references at the root. Do not rewrite arbitrary user schemas
    # into a wrapper that would change the meaning of #/$defs/... references.
    if not isinstance(schema, dict) or schema.get("type") != "object" or any(
            key in schema for key in ("$ref", "allOf", "anyOf", "oneOf", "not", "if", "propertyNames", "patternProperties")):
        raise ValueError("Codex triage requires a plain object schema")
    if "plan_markdown" in schema.get("properties", {}):
        raise ValueError("Codex triage reserves plan_markdown")
    schema.setdefault("properties", {})["plan_markdown"] = {"type": ["string", "null"]}
    RESULT["validator_for"](schema)
    return json.dumps(schema)


def wire_schema(schema_text):
    """Close declared objects for Codex strict output, leaving caller schemas intact.

    Optional fields must be supplied on the wire (empty strings/arrays can express
    no findings). The original schema still validates the result for consumers.
    """
    if not schema_text:
        return ""
    schema = RESULT["loads"](schema_text)

    def close(node):
        if not isinstance(node, dict):
            raise ValueError("Codex requires object-form schemas")
        if any(key in node for key in ("allOf", "oneOf", "not", "if", "then", "else",
                                        "dependentRequired", "dependentSchemas", "patternProperties")):
            raise ValueError("Unsupported Codex schema composition")
        if node.get("type") == "object" or "properties" in node:
            properties = node.setdefault("properties", {})
            if set(node.get("required", [])) - properties.keys():
                raise ValueError("Codex requires schemas for all required properties")
            if isinstance(node.get("additionalProperties"), dict):
                raise ValueError("Codex cannot generate arbitrary object keys")
            node["additionalProperties"] = False
            node["required"] = list(properties)
            for child in properties.values():
                close(child)
        for key in ("$defs", "definitions"):
            for child in node.get(key, {}).values():
                close(child)
        if "items" in node:
            close(node["items"])
        for child in node.get("anyOf", []):
            close(child)

    if not isinstance(schema, dict) or schema.get("type") != "object":
        raise ValueError("Codex structured output requires a root object")
    close(schema)
    RESULT["validator_for"](schema)
    return json.dumps(schema)


def materialize_plan(worktree, plan):
    # Publish only the validated plan into the existing harness artifact path.
    # Never follow worker-created directory/file symlinks into another location.
    with_dir = os.open(worktree, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    data_dir = None
    temporary = ".plan-" + uuid.uuid4().hex
    try:
        try:
            os.mkdir(".agent-data", mode=0o700, dir_fd=with_dir)
        except FileExistsError:
            pass
        data_dir = os.open(".agent-data", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=with_dir)
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=data_dir)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(plan)
        os.replace(temporary, "plan.md", src_dir_fd=data_dir, dst_dir_fd=data_dir)
    finally:
        if data_dir is not None:
            try:
                os.unlink(temporary, dir_fd=data_dir)
            except FileNotFoundError:
                pass
            os.close(data_dir)
        os.close(with_dir)


def invoke(request):
    phase = request.get("phase", "") if isinstance(request, dict) else ""
    try:
        worktree, capture_root = validate(request)
        effective_schema = phase_schema(phase, request["schema_json"])
        native_schema = wire_schema(effective_schema)
        writable_dirs = list(request.get("add_dirs", []))
        # Linked worktrees keep their index and shared objects/refs outside the
        # checkout. Native workspace-write otherwise prevents required commits.
        if request["sandbox"] == "workspace-write" and (worktree / ".git").exists():
            for flag in ("--absolute-git-dir", "--git-common-dir"):
                git_dir = subprocess.run(
                    ["git", "-C", str(worktree), "rev-parse", "--path-format=absolute", flag],
                    check=True, capture_output=True, text=True, timeout=15)
                path = Path(git_dir.stdout.strip()).resolve(strict=True)
                if not path.is_dir():
                    raise ValueError("Git metadata directory is unavailable")
                if str(path) not in writable_dirs:
                    writable_dirs.append(str(path))
    except Exception:
        return failure(phase, "Invalid Codex request, paths, schema or native settings")
    error = preflight()
    if error:
        return failure(phase, error)
    # Modes protect against other users; they are not a same-user sandbox.
    old_umask = os.umask(0o077)
    try:
        capture = Path(tempfile.mkdtemp(prefix=f"codex-{phase}-", dir=capture_root))
    except OSError:
        return failure(phase, "Cannot create Codex capture directory")
    finally:
        os.umask(old_umask)
    events_path, stderr_path, final_path = [capture / name for name in ("events", "stderr", "final")]
    schema_path = capture / "schema"
    argv = ["codex", "exec", "--json", "--color", "never", "--sandbox", request["sandbox"],
            "-c", 'approval_policy="never"', "--cd", str(worktree), "--output-last-message", str(final_path)]
    if not request.get("persist", False):
        argv.append("--ephemeral")
    if request["model"]:
        argv.append("--model=" + request["model"])
    if request.get("effort"):
        argv.extend(["-c", "model_reasoning_effort=" + json.dumps(request["effort"])])
    for path in writable_dirs:
        argv.extend(["--add-dir", path])
    if effective_schema:
        argv.extend(["--output-schema", str(schema_path)])
    argv.append("-")
    process = None
    interrupted = None

    def cancel(signum, frame):
        nonlocal interrupted
        interrupted = signum
        raise InterruptedError("Worker cancelled")

    def stop_group():
        nonlocal process
        if process is not None:
            worker, process = process, None
            try:
                os.killpg(worker.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                worker.wait(timeout=1)
            except subprocess.TimeoutExpired:
                pass
            try:
                os.killpg(worker.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            worker.wait()

    handlers = {sig: signal.signal(sig, cancel) for sig in (signal.SIGTERM, signal.SIGINT)}
    code = 0
    try:
        if effective_schema:
            schema_path.write_text(native_schema)
        with events_path.open("w") as events, stderr_path.open("w") as stderr:
            process = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=events, stderr=stderr,
                                       cwd=worktree, text=True, start_new_session=True)
            try:
                prompt = request["prompt"]
                if native_schema:
                    prompt += "\n\nReturn JSON matching the output schema. Supply every declared field; use empty strings or arrays for fields with no applicable content, where allowed by the schema."
                if phase == "TRIAGE":
                    prompt += "\n\nCodex triage output contract: do not write files. Instead of writing .agent-data/plan.md, return its full Markdown content in a plan_markdown field of your final JSON when action is plan_ready. The harness writes the plan artifact. For other actions omit plan_markdown or use null."
                process.communicate(prompt, timeout=request["timeout"])
                code = process.returncode
            except subprocess.TimeoutExpired:
                code = 124
            except InterruptedError:
                code = 128 + interrupted
            finally:
                # Ignore repeat cancellation while cleaning up the worker group.
                for sig in handlers:
                    signal.signal(sig, signal.SIG_IGN)
                stop_group()
        if code < 0:
            code = 128 - code
        result = RESULT["normalize_codex"](events_path.read_text(errors="replace"), phase, code,
                    effective_schema, read_final(final_path), stderr_path.read_text(errors="replace"))
        if phase == "TRIAGE" and result["status"] == "success":
            data = result["structured_output"]
            plan = data.pop("plan_markdown", None)
            try:
                if request["schema_json"]:
                    RESULT["validator_for"](RESULT["loads"](request["schema_json"])).validate(data)
                if data.get("action") == "plan_ready":
                    if not isinstance(plan, str) or not plan.strip():
                        raise ValueError("Missing plan")
                    materialize_plan(worktree, plan)
                result["result_text"] = json.dumps(data)
            except Exception:
                result.update(status="failed", structured_output=None, schema_status="invalid",
                              error={"kind": "schema", "message": "Codex triage result or plan artifact is invalid"})
        # Persist only decoded/scrubbed output. Raw or malformed streams may hide
        # escaped secrets; never keep them as diagnostic logs.
        (capture / "result.json").write_text(json.dumps(result) + "\n")
        (capture / "stderr.log").write_text(RESULT["scrub"](stderr_path.read_text(errors="replace")))
        return result
    except OSError:
        return failure(phase, "Unable to execute or capture Codex worker")
    finally:
        for sig in handlers:
            signal.signal(sig, signal.SIG_IGN)
        stop_group()
        for sig, handler in handlers.items():
            signal.signal(sig, handler)
        for path in (events_path, stderr_path, final_path, schema_path):
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "check-phase-schema":
        try:
            wire_schema(phase_schema(sys.argv[2], sys.stdin.read()))
        except Exception:
            raise SystemExit("Unsupported Codex phase schema")
        raise SystemExit(0)
    if sys.argv[1:] == ["preflight"]:
        error = preflight()
        if error:
            print(error, file=sys.stderr)
        raise SystemExit(1 if error else 0)
    if sys.argv[1:] != ["run"]:
        raise SystemExit("Expected preflight or run")
    try:
        request = RESULT["loads"](sys.stdin.read())
    except ValueError:
        request = None
    print(json.dumps(invoke(request)))

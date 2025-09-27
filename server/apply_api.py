from __future__ import annotations
import os, json, subprocess, sys
from flask import Blueprint, request, jsonify

bp = Blueprint("apply_api", __name__, url_prefix="/agent")

# LEB settings (same defaults as wrapper)
LEB_HOST = os.environ.get("LEB_HOST", "127.0.0.1")
LEB_PORT = int(os.environ.get("LEB_PORT", "8765"))
LEB_BASE = f"http://{LEB_HOST}:{LEB_PORT}"

def _leb_post_json(path: str, payload: dict, timeout: float = 12.0):
    import urllib.request, urllib.error  # stdlib only
    url = f"{LEB_BASE}{path}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        text = resp.read().decode("utf-8", errors="replace")
        try:
            return json.loads(text)
        except Exception:
            return {"ok": False, "raw": text, "status": getattr(resp, "status", None)}

def _local_run_step(step, tests, flags, retries):
    # Invoke drive_step.py directly; no dependency on run_with_capture.py
    argv = [sys.executable, os.path.join("tools", "py", "agentic", "drive_step.py"),
            "--step", str(step), "--apply"]

    # tests
    if isinstance(tests, (list, tuple)):
        argv += ["--tests", str(tests[0] if tests else "tests")]
    else:
        argv += ["--tests", str(tests or "tests")]

    # flags
    if flags:
        if isinstance(flags, (list, tuple)):
            argv += ["--pytest-flags"] + [str(x) for x in flags]
        else:
            argv += ["--pytest-flags", str(flags)]

    argv += ["--retries", str(int(max(0, retries)))]
    cp = subprocess.run(argv, capture_output=True, text=True)
    return {
        "ok": (cp.returncode == 0),
        "rc": cp.returncode,
        "stdout": cp.stdout,
        "stderr": cp.stderr,
        "argv": argv,
        "via": "local"
    }

@bp.post("/apply")
def agent_apply():
    """
    Body: { "step": "9.5a", "tests": "tests", "pytest_flags": ["-q"], "retries": 0 }
    Tries LEB first; if unavailable, runs drive_step.py locally.
    """
    data = request.get_json(silent=True) or {}
    step = str(data.get("step") or "").strip()
    tests = data.get("tests") or "tests"
    flags = data.get("pytest_flags") or ["-q"]
    retries = int(data.get("retries") or 0)

    if not step:
        return jsonify(ok=False, err="missing step"), 400

    # LEB first (if up)
    cmd = (
        "python tools/py/agentic/drive_step.py "
        f"--step {step} --apply --tests {tests} "
        f"--pytest-flags {' '.join(flags) if isinstance(flags,(list,tuple)) else flags} "
        f"--retries {retries}"
    )
    try:
        res = _leb_post_json("/run", {"cmd": cmd}, timeout=12.0)
        if isinstance(res, dict) and ("ok" in res or "rc" in res or "stdout" in res):
            return jsonify({"ok": True, "run": res, "via": "leb"})
    except Exception:
        pass

    # Local fallback
    res = _local_run_step(step, tests, flags, retries)
    return jsonify({"ok": True, "run": res, "via": "local"})

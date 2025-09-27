from __future__ import annotations
import sys, json, difflib, pathlib, subprocess
from flask import Flask, request, jsonify

# Exports used by tests:
ROOT = pathlib.Path(__file__).resolve().parents[1]
LEB_URL = "http://127.0.0.1:8765"

app = Flask(__name__)

def repo_root() -> pathlib.Path:
    return ROOT

def _run(cmd: list[str]) -> dict:
    """Run a subprocess; return rc/stdout/stderr plus args/cwd for diagnostics."""
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=str(repo_root()))
    return {
        "rc": p.returncode,
        "args": cmd,
        "cwd": str(repo_root()),
        "stdout": p.stdout,
        "stderr": p.stderr,
    }

def run_proposer(step_id: str, out: str) -> dict:
    # python -m tools.py.agentic.propose_for_step --id <id> --out <out> --force
    args = [sys.executable, "-m", "tools.py.agentic.propose_for_step",
            "--id", step_id, "--out", out, "--force"]
    res = _run(args)

    # Prefer the last stdout line if it looks like a path
    proposal_path = out
    if res["stdout"]:
        last = res["stdout"].strip().splitlines()[-1].strip()
        if last:
            proposal_path = last

    ok = (res["rc"] == 0)
    return {
        "ok": ok,
        "proposal_path": proposal_path,
        **res
    }

def _compute_after_text(before: str, mode: str, content: str) -> str:
    if mode == "append":
        return before + content
    if mode == "replace":
        return content
    # Unsupported modes ("patch") – keep as-is for preview.
    return before

def _diff_text(path_rel: str, before: str, after: str) -> str:
    before_lines = before.splitlines(keepends=True)
    after_lines  = after.splitlines(keepends=True)
    diff = difflib.unified_diff(
        before_lines, after_lines,
        fromfile=f"a/{path_rel}", tofile=f"b/{path_rel}"
    )
    return "".join(diff)

@app.post("/propose_step")
def propose_step():
    data = request.get_json(silent=True) or {}
    step_id = str(data.get("id", "")).strip()
    if not step_id:
        return jsonify({"ok": False, "error": "missing id"}), 400

    out = str(data.get("out", "")).strip() or str(repo_root()/"tmp"/"patches"/f"proposal_{step_id.replace('.','_')}.json")
    res = run_proposer(step_id, out)
    return jsonify(res), (200 if res.get("ok") else 500)

@app.post("/proposal_diff")
def proposal_diff():
    data = request.get_json(silent=True) or {}
    ppath = data.get("proposal_path")
    if not ppath:
        return jsonify({"ok": False, "error": "missing proposal_path"}), 400

    p = pathlib.Path(ppath)
    try:
        prop = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        return jsonify({"ok": False, "error": f"read/parse: {type(e).__name__}: {e}"}), 400

    actions = prop.get("actions") or prop.get("changes") or []
    diffs = []
    root = repo_root()
    for a in actions:
        path_rel = a.get("path")
        mode     = a.get("mode")
        content  = a.get("content", "")
        if not path_rel or not mode:
            continue
        abs_path = root / path_rel
        before = ""
        if abs_path.exists():
            try:
                before = abs_path.read_text(encoding="utf-8")
            except Exception:
                before = ""
        after = _compute_after_text(before, mode, content)
        d = _diff_text(path_rel, before, after)
        if d:
            diffs.append(d)

    diff_text = "\n".join(diffs)
    return jsonify({"ok": True, "diff": diff_text, "count": len(diffs)}), 200

@app.post("/proposal_apply")
def proposal_apply():
    """Apply (or dry-run) using tools.py.agentic.patch_apply and return parsed tool JSON under 'result'."""
    data = request.get_json(silent=True) or {}
    ppath = data.get("proposal_path")
    really_apply = bool(data.get("really_apply", False))
    if not ppath:
        return jsonify({"ok": False, "error": "missing proposal_path"}), 400

    args = [sys.executable, "-m", "tools.py.agentic.patch_apply", "--proposal", str(ppath)]
    if really_apply:
        args.append("--really-apply")

    res = _run(args)

    # Parse the tool stdout as JSON if possible
    result = None
    ok = False
    parse_error = None
    try:
        result = json.loads(res["stdout"]) if res["stdout"] else None
        ok = bool(result and result.get("ok"))
    except Exception as e:
        parse_error = f"{type(e).__name__}: {e}"
        ok = False

    payload = {
        "ok": ok,
        "really_apply": really_apply,
        "proposal_path": ppath,
        "result": result,  # <-- what the test asserts on
        "stdio": {
            "rc": res["rc"],
            "stdout_len": len(res["stdout"] or ""),
            "stderr_len": len(res["stderr"] or ""),
        },
        "args": res["args"],
        "cwd": res["cwd"],
    }
    if parse_error:
        payload["parse_error"] = parse_error
        payload["stdout_head"] = (res["stdout"] or "")[:400]

    return jsonify(payload), (200 if ok else 500)

@app.get("/healthz")
def healthz():
    return jsonify({"ok": True, "app": "proposal_api", "root": str(repo_root())})

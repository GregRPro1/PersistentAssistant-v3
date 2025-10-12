from __future__ import annotations
import os, subprocess
from pathlib import Path
from flask import Blueprint, request

def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]

def _tool(p: str) -> str:
    return str(_repo_root() / "tools" / "context" / p)

def _run_ps(script: str, args: list[str]) -> tuple[int, str]:
    cmd = ["pwsh","-NoProfile",_tool(script)] + args
    try:
        cp = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        return cp.returncode, (cp.stdout or "") + (cp.stderr or "")
    except Exception as e:
        return 1, f"ERR: {e}"

def register_ctx_panel(app):
    bp = Blueprint("pal_ctx", __name__)

    @bp.get("/context")
    def panel():
        master = os.environ.get("PAL_MASTER","PAL20251012")
        child  = os.environ.get("PAL_CHILD","PAL20251012B")
        html = (
            "<h2>Context Tools</h2>"
            "<form method='post'>"
            "<label>Master:</label><input name='master' value='{}'/><br/>"
            "<label>Child:</label><input name='child' value='{}'/><br/><br/>"
            "<button name='op' value='load'>Load Master</button>"
            "<button name='op' value='capture'>Capture Child</button>"
            "<button name='op' value='close'>Close Child</button>"
            "</form>"
        ).format(master, child)
        return html, 200

    @bp.post("/context")
    def action():
        op     = request.form.get("op")
        master = request.form.get("master","").strip()
        child  = request.form.get("child","").strip()
        if op == "load":
            rc, out = _run_ps("context_loader.ps1", ["-MasterId", master])
        elif op == "capture":
            rc, out = _run_ps("context_capture.ps1", ["-MasterId", master, "-ChildId", child])
        elif op == "close":
            rc, out = _run_ps("context_close.ps1", ["-MasterId", master, "-ChildId", child])
        else:
            rc, out = 1, "Unknown op"
        safe = out.replace("&","&amp;").replace("<","&lt;")
        return "<pre>"+safe+"</pre><p><a href='/context'>Back</a></p>", (200 if rc==0 else 500)

    try:
        app.register_blueprint(bp)
    except Exception:
        pass

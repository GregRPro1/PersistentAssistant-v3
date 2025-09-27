from __future__ import annotations
import os, json, time
from typing import Any, Dict, List
from flask import Blueprint, jsonify, request, Flask

# ------------------------------------------------------------------------------
# Public constants expected by tests
# ------------------------------------------------------------------------------
ROOT = os.path.abspath(os.getcwd())

# LEB configuration (match wrapper defaults)
LEB_HOST = os.environ.get("LEB_HOST", "127.0.0.1")
LEB_PORT = int(os.environ.get("LEB_PORT", "8765"))
LEB_URL  = f"http://{LEB_HOST}:{LEB_PORT}"

# ------------------------------------------------------------------------------
# Blueprint
# ------------------------------------------------------------------------------
bp = Blueprint("proposal_api", __name__, url_prefix="/agent")

def _default_suggestions() -> List[str]:
    return ["9.5a — Worker UX", "9.5b — Auto-process", "9.5c — Plan details"]

@bp.get("/propose")
def agent_propose_get():
    try:
        suggestions = _default_suggestions()
        return jsonify({"ok": True, "suggestions": suggestions, "ts": int(time.time())})
    except Exception as e:
        return jsonify({"ok": False, "err": f"{type(e).__name__}: {e}"}), 500

@bp.post("/propose")
def agent_propose_post():
    data = request.get_json(silent=True) or {}
    step = str(data.get("step") or "").strip()
    note = data.get("note")
    accepted = bool(step)

    # Best-effort: write a small marker so tooling can observe activity.
    try:
        status_path = os.environ.get("PA_STATUS_FILE", os.path.join("data", "runtime", "agent_status.json"))
        os.makedirs(os.path.dirname(status_path) or ".", exist_ok=True)
        prev: Dict[str, Any] = {}
        if os.path.isfile(status_path):
            try:
                prev = json.loads(open(status_path, "r", encoding="utf-8").read() or "{}")
            except Exception:
                prev = {}
        prev["last_accept"] = {"step": step or None, "note": note, "ts": int(time.time())}
        with open(status_path, "w", encoding="utf-8") as f:
            json.dump(prev, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    return jsonify({"ok": True, "accepted": accepted, "step": step or None, "note": note, "ts": int(time.time())})

def create_blueprint() -> Blueprint:
    return bp

# ------------------------------------------------------------------------------
# Test shim: expose a minimal Flask app for pytest to import as `app`
# ------------------------------------------------------------------------------
app = Flask("proposal_api_app")
app.register_blueprint(bp)

__all__ = ["bp", "app", "ROOT", "LEB_URL", "create_blueprint"]

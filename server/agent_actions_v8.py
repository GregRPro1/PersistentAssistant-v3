from flask import Blueprint, Response
import os, json, time, uuid, glob

actions_bp = Blueprint("agent_actions_v8", __name__)

def _root():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def _approvals_dir():
    d = os.path.join(_root(), "tmp", "phone", "approvals")
    os.makedirs(d, exist_ok=True)
    return d

def _j(o, code=200):
    return Response(json.dumps(o), mimetype="application/json", status=code)

@actions_bp.route("/agent/recent", methods=["GET"])
def agent_recent():
    try:
        d = _approvals_dir()
        fs = sorted(glob.glob(os.path.join(d, "approve_*.json")), key=os.path.getmtime, reverse=True)[:25]
        items = []
        for f in fs:
            try:
                items.append({"file": os.path.basename(f), "bytes": os.path.getsize(f)})
            except Exception:
                pass
        return _j({"ok": True, "approvals": items})
    except Exception as e:
        return _j({"ok": False, "err": str(e)}, 500)

@actions_bp.route("/agent/next2", methods=["GET","POST"])
def agent_next2():
    try:
        d = _approvals_dir()
        ts = int(time.time()); nonce = str(uuid.uuid4())
        p = os.path.join(d, f"approve_{ts}_{nonce}.json")
        with open(p, "w", encoding="utf-8") as f:
            f.write(json.dumps({"ok": True, "action": "NEXT", "ts": ts, "nonce": nonce}))
        sug = ["9.5a — Worker UX", "9.5b — Auto-process", "9.5c — Plan details"]
        return _j({"ok": True, "file": os.path.basename(p), "suggestions": sug})
    except Exception as e:
        return _j({"ok": False, "err": str(e)}, 500)

def attach_to_app(app):
    try:
        app.register_blueprint(actions_bp)
        return True
    except Exception:
        return False
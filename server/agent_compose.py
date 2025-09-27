from flask import Blueprint, request, jsonify
import os, sys, subprocess

bp = Blueprint("agent_compose", __name__)

def _read_token():
    p = os.path.join("config","phone_approvals.yaml")
    if not os.path.isfile(p): return None
    try:
        t = None
        for ln in open(p,"r",encoding="utf-8").read().splitlines():
            s = ln.strip()
            if s.lower().startswith("token:"):
                val = s.split(":",1)[1].strip().strip('"').strip("'")
                t = val or None
                break
        return t
    except Exception:
        return None

def _authorized(req):
    tok = _read_token()
    if not tok: return False
    hdr = req.headers.get("Authorization","")
    if not hdr.startswith("Bearer "): return False
    return hdr.split(" ",1)[1].strip() == tok

@bp.route("/agent/compose", methods=["GET","POST"])
def compose():
    if not _authorized(request):
        return jsonify({"ok": False, "err": "unauthorized"}), 401
    root = os.getcwd()
    py   = sys.executable or "python"
    script = os.path.join(root, "tools", "build_ai_prompt.py")
    if not os.path.isfile(script):
        return jsonify({"ok": False, "err": "builder not found"}), 500
    try:
        out = subprocess.check_output([py, script], text=True)
        path = (out or "").strip().splitlines()[-1]
        if not path or not os.path.isfile(path):
            return jsonify({"ok": False, "err": "builder did not return a path"}), 500
        txt = open(path,"r",encoding="utf-8").read()
        return jsonify({"ok": True, "path": path, "prompt": txt})
    except subprocess.CalledProcessError as e:
        return jsonify({"ok": False, "err": f"builder failed: {e}"}), 500
    except Exception as e:
        return jsonify({"ok": False, "err": str(e)}), 500

from flask import Blueprint, jsonify
import os, glob
try:
    from server.plan_view import build_plan_response
except Exception:
    build_plan_response = None
bp = Blueprint("agent_actions", __name__)
def approvals_dir(root):
    for b,_,_ in os.walk(root):
        p = os.path.join(b,"tmp","phone","approvals")
        if os.path.isdir(p): return p
    return os.path.join(root,"tmp","phone","approvals")
@bp.route("/agent/summary", methods=["GET"])
def agent_summary():
    root = os.getcwd()
    plan = {"active": None, "tree": [], "totals": {}}
    if build_plan_response:
        try: plan = build_plan_response(root) or plan
        except Exception: pass
    return jsonify({"ok": True, "plan": plan})
@bp.route("/agent/recent", methods=["GET"])
def agent_recent():
    root = os.getcwd(); d = approvals_dir(root)
    items=[]
    try:
        for f in sorted(glob.glob(os.path.join(d,"approve_*.json")), key=os.path.getmtime, reverse=True)[:12]:
            items.append({"file": os.path.basename(f), "ts": int(os.path.getmtime(f))})
    except Exception:
        pass
    return jsonify({"ok": True, "items": items})
@bp.route("/agent/approvals_count", methods=["GET"])
def approvals_count():
    root = os.getcwd(); d = approvals_dir(root)
    try: cnt = len([1 for _ in glob.glob(os.path.join(d,"approve_*.json"))])
    except Exception: cnt = 0
    return jsonify({"ok": True, "count": cnt})

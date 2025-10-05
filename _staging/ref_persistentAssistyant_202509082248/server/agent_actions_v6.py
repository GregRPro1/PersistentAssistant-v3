from flask import Blueprint, jsonify, request
import os, glob, time, json
try:
    from server.plan_view import build_plan_response
except Exception:
    build_plan_response = None
bp = Blueprint("agent_actions_v6", __name__)
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
        for f in sorted(glob.glob(os.path.join(d,"approve_*.json")), key=os.path.getmtime, reverse=True)[:25]:
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
@bp.route("/agent/next2", methods=["GET"])
def agent_next2():
    # Minimal fallback suggestions from plan or hard-coded if plan not available
    root = os.getcwd()
    suggestions = ["9.5a — Worker UX", "9.5b — Auto-process", "9.5c — Plan details"]
    if build_plan_response:
        try:
            pr = build_plan_response(root) or {}
            active = (pr.get("active") or {}).get("id") if isinstance(pr.get("active"), dict) else pr.get("active")
            if active and isinstance(pr.get("next_ids"), list) and pr["next_ids"]:
                suggestions = [str(x) for x in pr["next_ids"]]
        except Exception:
            pass
    return jsonify({"ok": True, "suggestions": suggestions, "ts": int(time.time())})

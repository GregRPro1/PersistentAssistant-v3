from flask import Blueprint, jsonify
import os, glob, time
try:
    import yaml
except Exception:
    yaml = None
try:
    from server.plan_view import build_plan_response as _pv_build
except Exception:
    _pv_build = None
bp = Blueprint("agent_actions_v7", __name__)
def _find_repo_root():
    root = os.getcwd()
    for b,_,fs in os.walk(root):
        if "project_plan_v3.yaml" in fs: return b
    return root
def _approvals_dir(root):
    for b,_,_ in os.walk(root):
        p = os.path.join(b,"tmp","phone","approvals")
        if os.path.isdir(p): return p
    return os.path.join(root,"tmp","phone","approvals")
def _fallback_plan():
    root=_find_repo_root()
    ypath=os.path.join(root,"project_plan_v3.yaml")
    tree=[]; active=None; totals={}
    if os.path.isfile(ypath) and yaml:
        try:
            data = yaml.safe_load(open(ypath,"r",encoding="utf-8")) or {}
            # best-effort: any list with dicts → renderable children
            def to_node(x):
                if isinstance(x,dict):
                    n={k:v for k,v in x.items() if not isinstance(v,(list,dict))};
                    ch=[]
                    for k,v in x.items():
                        if isinstance(v,list):
                            for it in v: ch.append(to_node(it))
                        elif isinstance(v,dict):
                            ch.append(to_node(v))
                    if ch: n["children"]=ch
                    return n
                else:
                    return {"title": str(x)}
            if isinstance(data,dict):
                # choose a plausible root list
                for k in ["phases","plan","steps","children"]:
                    if isinstance(data.get(k),list):
                        tree=[to_node(it) for it in data[k]]; break
                if not tree:
                    # flatten top-level
                    for k,v in data.items():
                        if isinstance(v,list):
                            tree=[to_node(it) for it in v]; break
                active = (data.get("active_step") or (data.get("state") or {}).get("current"))
        except Exception:
            pass
    return {"active": active, "tree": tree, "totals": totals}
@bp.route("/agent/plan", methods=["GET"])
def agent_plan():
    if _pv_build:
        try:
            root=_find_repo_root()
            res=_pv_build(root) or {}
            # normalize keys to {active, tree, totals}
            if "plan" in res: return jsonify(res)
            return jsonify({"plan": {"active": res.get("active"), "tree": res.get("tree") or [], "totals": res.get("totals") or {} }})
        except Exception:
            pass
    return jsonify({"plan": _fallback_plan()})
@bp.route("/agent/summary", methods=["GET"])
def agent_summary():
    # simple mirror of plan (client renders summary details)
    return agent_plan()
@bp.route("/agent/recent", methods=["GET"])
def agent_recent():
    root=_find_repo_root(); d=_approvals_dir(root)
    items=[]
    try:
        for f in sorted(glob.glob(os.path.join(d,"approve_*.json")), key=os.path.getmtime, reverse=True)[:25]:
            items.append({"file": os.path.basename(f), "ts": int(os.path.getmtime(f))})
    except Exception:
        pass
    return jsonify({"ok": True, "items": items})
@bp.route("/agent/approvals_count", methods=["GET"])
def approvals_count():
    root=_find_repo_root(); d=_approvals_dir(root)
    try: cnt = len([1 for _ in glob.glob(os.path.join(d,"approve_*.json"))])
    except Exception: cnt = 0
    return jsonify({"ok": True, "count": cnt})
@bp.route("/agent/next2", methods=["GET"])
def agent_next2():
    # minimal suggestions from plan; fall back to 9.5 tasks
    p = agent_plan().json.get("plan",{}) if hasattr(agent_plan(),"json") else {}
    nxt = p.get("next_ids") if isinstance(p.get("next_ids"),list) else None
    if not nxt: nxt = ["9.5a — Worker UX", "9.5b — Auto-process", "9.5c — Plan details"]
    return jsonify({"ok": True, "suggestions": nxt, "ts": int(time.time())})

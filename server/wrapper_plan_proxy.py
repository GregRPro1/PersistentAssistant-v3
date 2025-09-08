# server/wrapper_plan_proxy.py
from __future__ import annotations
import json
from typing import Any, Dict, Optional
from flask import jsonify, Response as _FlaskResponse

def _extract_json(obj: Any) -> Dict[str, Any]:
    try:
        if isinstance(obj, tuple) and len(obj) >= 1:
            obj = obj[0]
        if isinstance(obj, dict):
            return obj
        if isinstance(obj, _FlaskResponse):
            txt = obj.get_data(as_text=True)
            try:
                return json.loads(txt)
            except Exception:
                return {}
        if isinstance(obj, (str, bytes)):
            s = obj.decode("utf-8") if isinstance(obj, bytes) else obj
            try:
                return json.loads(s)
            except Exception:
                return {}
    except Exception:
        pass
    return {}

def _normalize_tree(tree: Any):
    def _norm(node: Any) -> Optional[Dict[str, Any]]:
        if not isinstance(node, dict):
            return None
        node = dict(node)
        node["id"] = str(node.get("id") or node.get("step_id") or node.get("name") or node.get("title") or "")
        node["title"] = node.get("title") or node.get("name") or node.get("desc") or node["id"]
        node["status"] = node.get("status") or node.get("state") or ""
        ch = node.get("children") or []
        if not isinstance(ch, list):
            ch = []
        node["children"] = [x for x in (_norm(c) for c in ch) if x]
        return node
    return [x for x in (_norm(n) for n in (tree or [])) if x]

def init_plan_proxy(app) -> bool:
    """
    Installs:
      - /__debug_plan_bind (always present)
      - a before_request guard that rebinds /agent/plan once to a normalizing proxy
    This survives late blueprint registration because the guard runs at request time.
    """
    state = app.config.setdefault("PLAN_PROXY_STATE", {"wired": False, "endpoint": None, "orig_name": None})

    def _resolve_ep() -> Optional[str]:
        try:
            for r in app.url_map.iter_rules():
                if str(r) == "/agent/plan":
                    return r.endpoint
        except Exception:
            pass
        return None

    def _agent_plan_proxy(*a, **kw):
        # call original if captured; else try wrapper.ep_agent_plan(); else empty plan
        orig = state.get("orig_func")
        try:
            if callable(orig):
                raw = orig(*a, **kw)
            else:
                from server.agent_sidecar_wrapper import ep_agent_plan  # type: ignore
                raw = ep_agent_plan()
        except Exception:
            try:
                from server.agent_sidecar_wrapper import ep_agent_plan  # type: ignore
                raw = ep_agent_plan()
            except Exception:
                raw = {"plan": {"tree": [], "totals": {}, "active": None}}

        data = _extract_json(raw)
        plan = data.get("plan") if isinstance(data, dict) and "plan" in data else data
        if not isinstance(plan, dict):
            plan = {}
        plan["tree"] = _normalize_tree(plan.get("tree") or [])
        plan.setdefault("totals", {})
        plan.setdefault("active", None)
        return jsonify({"ok": True, "plan": plan})

    def ep_debug_plan_bind():
        ep = _resolve_ep()
        vf = app.view_functions.get(ep) if ep else None
        return jsonify({
            "ok": True,
            "binding": {
                "endpoint": ep,
                "view_func": getattr(vf, "__name__", str(vf)),
                "proxied": getattr(vf, "__name__", "") == "_agent_plan_proxy",
                "wired": bool(app.config.get("PLAN_PROXY_STATE", {}).get("wired")),
            },
            "routes": [{"rule": str(r), "endpoint": r.endpoint}
                       for r in app.url_map.iter_rules()
                       if str(r).startswith("/agent")]
        })

    # Always expose the debug endpoint (even before the guard wires)
    try:
        app.add_url_rule("/__debug_plan_bind", "pa_debug_plan_bind", ep_debug_plan_bind, methods=["GET"])
    except Exception:
        pass

    @app.before_request
    def _bind_guard():
        st = app.config.get("PLAN_PROXY_STATE", {})
        if st.get("wired"):
            return
        ep = _resolve_ep()
        if not ep:
            return
        cur = app.view_functions.get(ep)
        name = getattr(cur, "__name__", "")
        if name != "_agent_plan_proxy":
            st["endpoint"] = ep
            st["orig_name"] = name
            st["orig_func"] = cur
            app.view_functions[ep] = _agent_plan_proxy
            st["wired"] = True
            print(f"[plan-proxy] rebound /agent/plan -> _agent_plan_proxy (ep='{ep}', orig='{name}')")

    return True

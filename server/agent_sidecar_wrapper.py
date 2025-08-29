# server/agent_sidecar_wrapper.py
# Robust sidecar wrapper that guarantees required /agent/* endpoints exist
# and delegates to the real sidecar app if present.

import os
import sys
import time
import json
import glob
import re
import importlib
import importlib.util

from flask import Flask, jsonify, make_response, send_from_directory, request, Response

# ---------------------------------------------------------------------
# Constants / paths
# ---------------------------------------------------------------------
REPO = os.path.abspath(os.getcwd())
PWA_DIR = os.path.join(REPO, "web", "pwa")
SIG = "wrap-stable-v1"

def log(*a):
    print(*a, flush=True)

# ---------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------
def no_cache(resp):
    try:
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
    except Exception:
        pass
    return resp

def approvals_dir():
    p = os.path.join(REPO, "tmp", "phone", "approvals")
    try:
        os.makedirs(p, exist_ok=True)
    except Exception:
        pass
    return p

def json_resp(o, status=200):
    try:
        return Response(json.dumps(o), mimetype="application/json", status=status)
    except Exception:
        return Response('{"ok":false}', mimetype="application/json", status=500)

def have_rule(flask_app, rule_text):
    try:
        for r in flask_app.url_map.iter_rules():
            if str(r) == rule_text:
                return True
    except Exception:
        pass
    return False

def ensure_rule(flask_app, rule, endpoint, view_func, methods=("GET",)):
    if not have_rule(flask_app, rule):
        try:
            flask_app.add_url_rule(rule, endpoint=endpoint, view_func=view_func, methods=list(methods))
            log("[wrapper]", SIG, "bound", rule, "->", endpoint)
        except Exception as e:
            log("[wrapper]", SIG, "add_url_rule failed for", rule, ":", e)

# ---------------------------------------------------------------------
# Try to load a real sidecar app; else create our own
# ---------------------------------------------------------------------
def load_sidecar_app():
    # Try package import: server.agent_sidecar:app
    try:
        m = importlib.import_module("server.agent_sidecar")
        app = getattr(m, "app", None)
        if app is not None:
            log("[wrapper]", SIG, "imported server.agent_sidecar.app (package)")
            return app
    except Exception as e:
        log("[wrapper]", SIG, "package import failed:", e)

    # Try by file path
    try:
        path = os.path.join(REPO, "server", "agent_sidecar.py")
        if os.path.isfile(path):
            spec = importlib.util.spec_from_file_location("agent_sidecar", path)
            mod = importlib.util.module_from_spec(spec)
            sys.modules["agent_sidecar"] = mod
            spec.loader.exec_module(mod)  # type: ignore[attr-defined]
            app = getattr(mod, "app", None)
            if app is not None:
                log("[wrapper]", SIG, "imported server/agent_sidecar.py (file)")
                return app
    except Exception as e:
        log("[wrapper]", SIG, "file import failed:", e)

    return None

app = load_sidecar_app()
if app is None:
    app = Flask(__name__, static_folder=None)
    log("[wrapper]", SIG, "created internal Flask app")

    # Optional: extension registry (no-op if absent)
    try:
        from server.app_registry import register_extensions
        try:
            register_extensions(app)  # type: ignore[misc]
        except Exception:
            pass
    except Exception:
        pass

# ---------------------------------------------------------------------
# Diagnostics / metadata endpoints
# ---------------------------------------------------------------------
def routes_list():
    out = []
    try:
        for r in app.url_map.iter_rules():
            out.append({"rule": str(r), "methods": sorted(list(r.methods or []))})
    except Exception:
        pass
    return out

def ep___routes__():
    return jsonify({"ok": True, "routes": routes_list(), "sig": SIG})

def ep_health():
    return jsonify({"ok": True, "sig": SIG})

def ep_agent_routes():
    # Alias expected by your auto-health
    try:
        rules = [str(r) for r in app.url_map.iter_rules()]
    except Exception:
        rules = []
    return jsonify({"ok": True, "routes": rules, "sig": SIG})

def ep_agent_sig():
    return jsonify({"ok": True, "sig": SIG})

# ---------------------------------------------------------------------
# PWA assets
# ---------------------------------------------------------------------
def ep_pwa_agent():
    if not os.path.isdir(PWA_DIR):
        return ("pwa dir missing", 404)
    resp = make_response(send_from_directory(PWA_DIR, "agent.html"))
    return no_cache(resp)

def ep_pwa_static(filename):
    if not os.path.isdir(PWA_DIR):
        return ("pwa dir missing", 404)
    resp = make_response(send_from_directory(PWA_DIR, filename))
    return no_cache(resp)

def ep_static_passthru(filename):
    if not os.path.isdir(PWA_DIR):
        return ("pwa dir missing", 404)
    resp = make_response(send_from_directory(PWA_DIR, filename))
    return no_cache(resp)

# ---------------------------------------------------------------------
# Plan view (fallback) and summary
# ---------------------------------------------------------------------
def build_plan_fallback():
    try:
        try:
            import yaml  # optional
        except Exception:
            yaml = None  # type: ignore[assignment]

        plan_path = None
        for base, _dirs, files in os.walk(REPO):
            if "project_plan_v3.yaml" in files:
                plan_path = os.path.join(base, "project_plan_v3.yaml")
                break

        active = None
        tree = []
        totals = {"done": 0, "in_progress": 0, "blocked": 0, "todo": 0}
        txt = ""

        if plan_path and os.path.isfile(plan_path):
            txt = open(plan_path, "r", encoding="utf-8").read()
            doc = yaml.safe_load(txt) if yaml else {}
        else:
            doc = {}

        nodes = []

        def walk_all(x):
            st = [x]
            while st:
                v = st.pop()
                if isinstance(v, dict):
                    yield v
                    st.extend(list(v.values()))
                elif isinstance(v, list):
                    st.extend(v)

        for n in walk_all(doc):
            if not isinstance(n, dict):
                continue
            _id = str(n.get("id") or n.get("step_id") or "").strip()
            if not _id:
                continue
            title = str(n.get("name") or n.get("title") or n.get("desc") or "").strip()
            status = str(n.get("status") or n.get("state") or "").strip()
            nodes.append({"id": _id, "title": title, "status": status, "children": []})

        if not nodes and txt:
            ids = re.findall(r'^[ \t]*(?:id|step_id)\s*:\s*([\w\.-]+)', txt, flags=re.MULTILINE)
            nodes = [{"id": i, "title": "", "status": "", "children": []} for i in sorted(set(ids))]

        def classify(s):
            s = (s or "").lower()
            if s in ("done", "complete", "finished"):
                return "done"
            if s in ("in_progress", "active", "working", "running"):
                return "in_progress"
            if s in ("blocked", "error", "fail", "failed"):
                return "blocked"
            return "todo"

        def dsum(a, b):
            for k in ("done", "in_progress", "blocked", "todo"):
                a[k] = a.get(k, 0) + b.get(k, 0)
            return a

        def count(node):
            c = {"done": 0, "in_progress": 0, "blocked": 0, "todo": 0}
            if node.get("id"):
                c[classify(node.get("status"))] += 1
            for ch in node.get("children") or []:
                dsum(c, count(ch))
            node["counts"] = c
            return c

        groups = {}
        for nd in nodes:
            major = nd["id"].split(".", 1)[0] if "." in nd["id"] else nd["id"]
            groups.setdefault(major, []).append(nd)

        for major in sorted(groups.keys(), key=lambda x: (len(x), x)):
            phase = {
                "id": str(major),
                "title": "Phase " + str(major),
                "status": "",
                "children": sorted(groups[major], key=lambda x: x["id"]),
            }
            dsum(totals, count(phase))
            tree.append(phase)

        return {"active": None, "tree": tree, "totals": totals}
    except Exception as e:
        log("[wrapper]", SIG, "plan fallback error:", e)
        return {"active": None, "tree": [], "totals": {}, "err": str(e)}

def ep_agent_plan():
    # Use server.plan_view.build_plan_response if available
    try:
        from server.plan_view import build_plan_response  # type: ignore[import]
        try:
            return jsonify({"ok": True, "plan": build_plan_response(REPO)})
        except Exception as e:
            return jsonify({"ok": True, "plan": {"active": None, "tree": [], "totals": {}, "err": str(e)}})
    except Exception:
        return jsonify({"ok": True, "plan": build_plan_fallback()})

def ep_agent_summary():
    return jsonify({"ok": True, "summary": {"active_step": None, "desc": "fallback", "next_ids": []}})


def ep_daily_status_fallback():
    """
    Return data/status/daily_status.json if present; else a minimal OK stub.
    """
    try:
        path = os.path.join(REPO, "data", "status", "daily_status.json")
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                return Response(f.read(), mimetype="application/json", status=200)
        else:
            return jsonify({"ok": True, "last_run": 0, "summary": "no file"}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# ---------------------------------------------------------------------
# Approvals / worker / recent / next2
# ---------------------------------------------------------------------
def ep_agent_ac():
    try:
        n = len([x for x in os.listdir(approvals_dir()) if x.endswith(".json")])
    except Exception:
        n = 0
    return jsonify({"ok": True, "count": n})

def ep_worker_status():
    # Minimal stub; adapt to your worker if present
    worker = {"calls": 0, "tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0, "last_ts": 0, "last_err": "", "last_reply_len": 0}
    return jsonify({"ok": True, "worker": worker})

def ep_agent_recent():
    try:
        d = approvals_dir()
        files = sorted(glob.glob(os.path.join(d, "approve_*.json")), key=os.path.getmtime, reverse=True)[:25]
        items = []
        for f in files:
            try:
                items.append({"file": os.path.basename(f), "bytes": os.path.getsize(f)})
            except Exception:
                pass
        return jsonify({"ok": True, "approvals": items})
    except Exception as e:
        return jsonify({"ok": False, "err": str(e)}), 500

def ep_agent_next2():
    try:
        d = approvals_dir()
        ts = int(time.time())
        nonce = "%d_%d" % (ts, os.getpid())
        path = os.path.join(d, "approve_%s.json" % nonce)
        with open(path, "w", encoding="utf-8") as f:
            f.write(json.dumps({"ok": True, "action": "NEXT", "ts": ts, "nonce": nonce}))
        suggestions = ["9.5a - Worker UX", "9.5b - Auto-process", "9.5c - Plan details"]
        return jsonify({"ok": True, "file": os.path.basename(path), "suggestions": suggestions})
    except Exception as e:
        return jsonify({"ok": False, "err": str(e)}), 500

# ---------------------------------------------------------------------
# UI / WS stubs
# ---------------------------------------------------------------------
def ep_agent_ui():
    html = '<html><body><a href="/pwa/agent">Open PWA Agent UI</a></body></html>'
    return make_response(html, 200)

def ep_agent_ws():
    return jsonify({"ok": True, "ws": "stub"})

# ---------------------------------------------------------------------
# Optional blueprints (best-effort)
# ---------------------------------------------------------------------
def try_register_blueprints(flask_app):
    for mod in ("server.agent_actions_v5", "server.agent_actions_v6", "server.agent_actions_v7", "server.agent_actions_v8"):
        try:
            m = importlib.import_module(mod)
            bp = getattr(m, "bp", None)
            if bp is not None:
                flask_app.register_blueprint(bp)
                log("[wrapper]", SIG, "registered blueprint from", mod)
        except Exception:
            pass
    try:
        from server.agent_compose import bp as compose_bp  # type: ignore[import]
        flask_app.register_blueprint(compose_bp)
        log("[wrapper]", SIG, "registered compose blueprint")
    except Exception:
        pass

    # optional daily status micro-endpoint
    try:
        from server.micro_daily_status import bp as daily_bp
        flask_app.register_blueprint(daily_bp)
        log("[wrapper] bound /agent/daily_status -> daily_status")
    except Exception as _e:
        # keep wrapper robust if the optional micro is missing or broken
        pass

        # optional new-project micro-endpoint
    try:
        from server.micro_projects import bp as projects_bp  # type: ignore[import]
        flask_app.register_blueprint(projects_bp)
        log("[wrapper] bound /agent/project/new -> micro_projects")
    except Exception:
        pass


try_register_blueprints(app)

# ---------------------------------------------------------------------
# Bind routes (only if missing) so we do not collide with a real sidecar
# ---------------------------------------------------------------------
# Diagnostics
ensure_rule(app, "/__routes__",      "pa_routes_list",       ep___routes__)
ensure_rule(app, "/health",          "pa_health",            ep_health)
ensure_rule(app, "/agent_routes",    "pa_agent_routes",      ep_agent_routes)
ensure_rule(app, "/agent/_sig",      "pa_sig",               ep_agent_sig)

# PWA
ensure_rule(app, "/pwa/agent",       "pa_pwa_agent",         ep_pwa_agent)
ensure_rule(app, "/pwa/<path:filename>", "pa_pwa_static",    ep_pwa_static)
ensure_rule(app, "/static/<path:filename>", "pa_static",     ep_static_passthru)

# Plan / summary
ensure_rule(app, "/agent/plan",      "pa_plan_fallback",     ep_agent_plan)
ensure_rule(app, "/agent/summary",   "pa_summary_fallback",  ep_agent_summary)
ensure_rule(app, "/agent/daily_status", "pa_daily_status_fallback", ep_daily_status_fallback)

# Approvals / worker / recent / next2
ensure_rule(app, "/agent/approvals_count", "pa_approvals_count", ep_agent_ac)
ensure_rule(app, "/agent/ac",              "pa_ac_short",        ep_agent_ac)
ensure_rule(app, "/agent/worker_status",   "pa_worker_status",   ep_worker_status)
ensure_rule(app, "/agent/recent",          "pa_recent",          ep_agent_recent, methods=("GET",))
ensure_rule(app, "/agent/next2",           "pa_next2",           ep_agent_next2,  methods=("GET","POST"))

# UI / WS
ensure_rule(app, "/agent/ui",          "pa_ui",            ep_agent_ui)
ensure_rule(app, "/agent/ws",          "pa_ws",            ep_agent_ws)

ensure_rule(app, "/agent/daily_status", "pa_daily_status_fallback", ep_daily_status_fallback, methods=("GET",))


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------
if __name__ == "__main__":
    host = os.environ.get("PA_SIDECAR_HOST", "0.0.0.0")
    port = int(os.environ.get("PA_SIDECAR_PORT", "8782"))
    log("[wrapper]", SIG, "running on %s:%d" % (host, port))
    # threaded=True for lightweight concurrency; disable reloader for wrapper use
    app.run(host=host, port=port, threaded=True, use_reloader=False)

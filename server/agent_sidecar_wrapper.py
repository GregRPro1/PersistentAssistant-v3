from server.app_registry import register_extensions
import os, sys, time, importlib, importlib.util, re, json
from flask import Flask, send_from_directory, jsonify, make_response, request

REPO = os.getcwd()
PWA_DIR = os.path.join(REPO, "web", "pwa")
SIG = "wrap-v4"
LOG = lambda *a, **k: print(*a, **k, flush=True)

def _no_cache(resp):
    try:
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
    except Exception:
        pass
    return resp

# Try to import sidecar app, else create one
app = None
try:
    m = importlib.import_module("server.agent_sidecar")
    app = getattr(m, "app", None)
    if app: LOG("[wrapper]", SIG, "imported server.agent_sidecar.app (package)")
except Exception as e:
    LOG("[wrapper]", SIG, "package import failed:", e)

if app is None:
    try:
        p = os.path.join(REPO, "server", "agent_sidecar.py")
        spec = importlib.util.spec_from_file_location("agent_sidecar", p)
        mod = importlib.util.module_from_spec(spec)
        sys.modules["agent_sidecar"] = mod
        spec.loader.exec_module(mod)
        app = getattr(mod, "app", None)
        if app: LOG("[wrapper]", SIG, "imported server/agent_sidecar.py (file)")
    except Exception as e:
        LOG("[wrapper]", SIG, "file import failed:", e)

if app is None:
app = Flask(__name__, static_folder=None)
try:
    register_extensions(app)
except Exception:
    pass
try:
    app.register_blueprint(_pa_actions_bp)
except Exception:
    pass
    @app.route("/agent/summary")
    def _fallback_summary():
        return jsonify({"ok": True, "summary": {"active_step": None, "desc": "fallback", "next_ids": []}})

# Diagnostics + PWA
@app.route("/__routes__")
def __routes__():
    out=[]
    try:
        for r in app.url_map.iter_rules():
            out.append({"rule":str(r), "methods":sorted(list(r.methods or []))})
    except Exception:
        pass
    return jsonify({"ok":True, "routes":out, "sig":SIG})

@app.route("/health")
def _health():
    return jsonify({"ok": True, "sig": SIG})

@app.route("/pwa/agent")
def pwa_agent():
    if not os.path.isdir(PWA_DIR): return ("pwa dir missing", 404)
    resp = make_response(send_from_directory(PWA_DIR, "agent.html"))
    return _no_cache(resp)

@app.route("/pwa/<path:filename>")
def pwa_static(filename):
    if not os.path.isdir(PWA_DIR): return ("pwa dir missing", 404)
    resp = make_response(send_from_directory(PWA_DIR, filename))
    return _no_cache(resp)

@app.route("/static/<path:filename>")
def static_passthru(filename):
    if not os.path.isdir(PWA_DIR): return ("pwa dir missing", 404)
    resp = make_response(send_from_directory(PWA_DIR, filename))
    return _no_cache(resp)

# Signature endpoint so we know which wrapper is live
@app.route("/agent/_sig")
def agent_sig():
    return jsonify({"ok": True, "sig": SIG})

# FORCE-bind /agent/* fallbacks (unique endpoint names)
def _ensure(rule, endpoint, func, methods=None):
    try:
        app.add_url_rule(rule, endpoint=endpoint, view_func=func, methods=methods)
        LOG("[wrapper]", SIG, "bound", rule, "->", endpoint)
    except Exception as e:
        LOG("[wrapper]", SIG, "add_url_rule skipped for", rule, ":", e)

APPROVALS_DIR = os.path.join(REPO,"tmp","phone","approvals")
def _approvals_count():
    try:
        n = len([x for x in os.listdir(APPROVALS_DIR) if x.endswith(".json")]) if os.path.isdir(APPROVALS_DIR) else 0
    except Exception:
        n = 0
    return jsonify({"ok":True,"count":n})

WORKER = {"calls":0,"tokens_in":0,"tokens_out":0,"cost_usd":0.0,"last_ts":0,"last_err":"","last_reply_len":0}
def _worker_status():
    return jsonify({"ok":True,"worker":WORKER})

def _plan_resp():
    try:
        try:
            import yaml
        except Exception:
            yaml = None
        plan_path=None
        for base,dirs,files in os.walk(REPO):
            if "project_plan_v3.yaml" in files:
                plan_path = os.path.join(base,"project_plan_v3.yaml"); break
        active=None; tree=[]; totals={"done":0,"in_progress":0,"blocked":0,"todo":0}
        txt=""
        if plan_path and os.path.isfile(plan_path):
            txt = open(plan_path,"r",encoding="utf-8").read()
            doc = yaml.safe_load(txt) if yaml else {}
        else:
            doc = {}
        # collect nodes
        nodes=[]
        def all_nodes(x):
            st=[x]
            while st:
                v=st.pop()
                if isinstance(v,dict):
                    yield v; st.extend(list(v.values()))
                elif isinstance(v,list):
                    st.extend(v)
        for n in all_nodes(doc):
            if not isinstance(n,dict): continue
            _id=str(n.get("id") or n.get("step_id") or "").strip()
            if not _id: continue
            title=str(n.get("name") or n.get("title") or n.get("desc") or "").strip()
            status=str(n.get("status") or n.get("state") or "").strip()
            nodes.append({"id":_id,"title":title,"status":status,"children":[]})
        if not nodes and txt:
            ids = re.findall(r'^[ \t]*(?:id|step_id)\s*:\s*([\w\.-]+)', txt, flags=re.MULTILINE)
            nodes = [{"id":i,"title":"","status":"","children":[]} for i in sorted(set(ids))]
        # group by major
        groups={}
        for nd in nodes:
            major = nd["id"].split(".",1)[0] if "." in nd["id"] else nd["id"]
            groups.setdefault(major,[]).append(nd)
        def _classify(s):
            s=(s or "").lower()
            if s in ("done","complete","finished"): return "done"
            if s in ("in_progress","active","working","running"): return "in_progress"
            if s in ("blocked","error","fail","failed"): return "blocked"
            return "todo"
        def _sum(a,b):
            for k in ("done","in_progress","blocked","todo"): a[k]=a.get(k,0)+b.get(k,0)
            return a
        def _count(node):
            c={"done":0,"in_progress":0,"blocked":0,"todo":0}
            if node.get("id"): c[_classify(node.get("status"))]+=1
            for ch in node.get("children") or []: _sum(c,_count(ch))
            node["counts"]=c; return c
        for major in sorted(groups.keys(), key=lambda x:(len(x),x)):
            phase={"id":str(major),"title":"Phase "+str(major),"status":"","children":sorted(groups[major], key=lambda x:x["id"])}
            _sum(totals,_count(phase)); tree.append(phase)
        if isinstance(doc,dict): active=doc.get("active_step")
        return jsonify({"ok":True,"plan":{"active":active,"tree":tree,"totals":totals}})
    except Exception as e:
        LOG("[wrapper]", SIG, "plan error:", e)
        return jsonify({"ok":True,"plan":{"active":None,"tree":[], "totals":{}}})

# register
_ensure("/agent/_sig","pa_sig", agent_sig, methods=["GET"])
_ensure("/agent/approvals_count","pa_approvals_count_fallback", _approvals_count, methods=["GET"])
_ensure("/agent/worker_status","pa_worker_status_fallback", _worker_status, methods=["GET"])
_ensure("/agent/plan","pa_plan_fallback", _plan_resp, methods=["GET"])

if __name__ == "__main__":
    host = os.environ.get("PA_SIDECAR_HOST","0.0.0.0")
    port = int(os.environ.get("PA_SIDECAR_PORT","8782"))
    LOG("[wrapper]", SIG, "running on {}:{}".format(host, port))
    app.run(host=host, port=port, threaded=True, use_reloader=False)

# PA_PLAN_VIEW_V2
try:
    from server.plan_view import build_plan_response
    def _pa_plan_v2():
        try:
            return jsonify({"ok": True, "plan": build_plan_response(os.getcwd())})
        except Exception as e:
            return jsonify({"ok": True, "plan": {"active": None, "tree": [], "totals": {}, "err": str(e)}})
    # Replace existing endpoint if present, else register
    if "agent_plan" in app.view_functions:
        app.view_functions["agent_plan"] = _pa_plan_v2
    else:
        app.add_url_rule("/agent/plan","agent_plan", _pa_plan_v2, methods=["GET"])
except Exception as _e:
    pass

# PA_AGENT_ACTIONS_V5
try:
    from server.agent_actions_v5 import bp as _aa
    app.register_blueprint(_aa)
except Exception as _e:
    pass


# PA_AGENT_ACTIONS_V6
try:
    from server.agent_actions_v6 import bp as _aav6
    app.register_blueprint(_aav6)
except Exception as _e:
    pass


# PA_AGENT_ACTIONS_V7
try:
    from server.agent_actions_v7 import bp as _aav7
    app.register_blueprint(_aav7)
except Exception as _e:
    pass

# --- fallback: /agent/recent ---
try:
  import os, json, glob
  import flask
except Exception as _e:
  pass
def _wrap_json(obj, code=200):
  return flask.Response(json.dumps(obj), mimetype="application/json", status=code)
try:
  ROOT  # noqa
except Exception:
  import os as _os
  ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), ".."))
@wrap_app.route("/agent/recent", methods=["GET"])
def pa_recent_fallback():
  try:
    root = os.path.join(ROOT, "tmp", "phone", "approvals")
    os.makedirs(root, exist_ok=True)
    files = sorted(glob.glob(os.path.join(root, "approve_*.json")))[-20:]
    items = []
    for p in reversed(files):
      try:
        items.append({"file": os.path.basename(p), "bytes": os.path.getsize(p)})
      except Exception:
        pass
    return _wrap_json({"ok": True, "approvals": items})
  except Exception as e:
    return _wrap_json({"ok": False, "err": str(e)}, 500)

# --- fallback: /agent/next2 ---
try:
  import os, json, time, uuid
  import flask
except Exception as _e:
  pass
@wrap_app.route("/agent/next2", methods=["GET","POST"])
def pa_next2_fallback():
  try:
    root = os.path.join(ROOT, "tmp", "phone", "approvals")
    os.makedirs(root, exist_ok=True)
    ts = int(time.time()); nonce = str(uuid.uuid4())
    path = os.path.join(root, f"approve_{ts}_{nonce}.json")
    with open(path, "w", encoding="utf-8") as f:
      f.write(json.dumps({"ok": True, "action": "NEXT", "ts": ts, "nonce": nonce}))
    return flask.Response(json.dumps({"ok": True, "file": os.path.basename(path)}), mimetype="application/json")
  except Exception as e:
    return flask.Response(json.dumps({"ok": False, "err": str(e)}), mimetype="application/json", status=500)
# ==== HARD_BIND_AGENT_V2 ====
# Robust ensure of /agent/recent and /agent/next2 even if sidecar omitted them.
try:
    # pick an app to bind
    _APP = None
    try:
        _APP = wrap_app  # wrapper-created Flask app
    except NameError:
        try:
            _APP = app   # fallback if called 'app'
        except NameError:
            _APP = None
    if _APP is not None:
        import os, json, time, uuid, glob
        from flask import Response

        try:
            ROOT
        except NameError:
            ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

        def _json(obj, status=200):
            return Response(json.dumps(obj), mimetype="application/json", status=status)

        def _ensure(rule, func, methods=('GET',)):
            try:
                have = {r.rule for r in _APP.url_map.iter_rules()}
            except Exception:
                have = set()
            if rule not in have:
                _APP.add_url_rule(rule, view_func=func, methods=list(methods))

        def _approvals_dir():
            p=os.path.join(ROOT,'tmp','phone','approvals')
            try: os.makedirs(p, exist_ok=True)
            except Exception: pass
            return p

        def _recent_view():
            try:
                d=_approvals_dir()
                files=sorted(glob.glob(os.path.join(d,'approve_*.json')), key=os.path.getmtime, reverse=True)[:25]
                items=[]
                for f in files:
                    try:
                        items.append({"file": os.path.basename(f), "bytes": os.path.getsize(f)})
                    except Exception:
                        pass
                return _json({"ok": True, "approvals": items})
            except Exception as e:
                return _json({"ok": False, "err": str(e)}, 500)

        def _next2_view():
            try:
                d=_approvals_dir()
                ts=int(time.time()); nonce=str(uuid.uuid4())
                path=os.path.join(d, f"approve_{ts}_{nonce}.json")
                with open(path,'w',encoding='utf-8') as f:
                    f.write(json.dumps({"ok": True, "action": "NEXT", "ts": ts, "nonce": nonce}))
                # lightweight suggestions if planner not wired
                suggestions=["9.5a — Worker UX", "9.5b — Auto-process", "9.5c — Plan details"]
                return _json({"ok": True, "file": os.path.basename(path), "suggestions": suggestions})
            except Exception as e:
                return _json({"ok": False, "err": str(e)}, 500)

        _ensure('/agent/recent',  _recent_view, methods=('GET',))
        _ensure('/agent/next2',   _next2_view,  methods=('GET','POST'))
except Exception:
    pass
# ==== HARD_BIND_AGENT_V2 END ====
# ==== DEFERRED_ATTACH_V8 ====
try:
    from server.agent_actions_v8 import attach_to_app as _pa_attach
except Exception:
    _pa_attach = None

def _pa_try_attach_once():
    try:
        g = globals()
        app = g.get("wrap_app") or g.get("app")
        if app and _pa_attach:
            _pa_attach(app)
    except Exception:
        pass

_pa_try_attach_once()

import threading, time as _patime
def _pa_defer():
    for _ in range(60):
        g = globals()
        app = g.get("wrap_app") or g.get("app")
        if app:
            try:
                if _pa_attach:
                    _pa_attach(app)
            except Exception:
                pass
            return
        _patime.sleep(0.25)
threading.Thread(target=_pa_defer, daemon=True).start()
# ==== DEFERRED_ATTACH_V8 END ====
# ==== HARD_ENSURE_AGENT_RECENT_NEXT2_V3 ====
def _pa_get_app():
    g = globals()
    return g.get("wrap_app") or g.get("app")

try:
    import os, json, time, uuid, glob
    from flask import Response
except Exception:
    pass

try:
    ROOT
except NameError:
    import os as _os
    ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), ".."))

def _pa_json(o, status=200):
    try:
        return Response(json.dumps(o), mimetype="application/json", status=status)
    except Exception:
        return Response('{"ok":false}', mimetype="application/json", status=500)

def _pa_approvals_dir():
    d = os.path.join(ROOT, 'tmp', 'phone', 'approvals')
    try:
        os.makedirs(d, exist_ok=True)
    except Exception:
        pass
    return d

def _pa_recent_view():
    try:
        d = _pa_approvals_dir()
        fs = sorted(glob.glob(os.path.join(d, 'approve_*.json')), key=os.path.getmtime, reverse=True)[:25]
        items = []
        for f in fs:
            try:
                items.append({"file": os.path.basename(f), "bytes": os.path.getsize(f)})
            except Exception:
                pass
        return _pa_json({"ok": True, "approvals": items})
    except Exception as e:
        return _pa_json({"ok": False, "err": str(e)}, 500)

def _pa_next2_view():
    try:
        d = _pa_approvals_dir()
        ts = int(time.time()); nonce = str(uuid.uuid4())
        p = os.path.join(d, f"approve_{ts}_{nonce}.json")
        with open(p, 'w', encoding='utf-8') as f:
            f.write(json.dumps({"ok": True, "action": "NEXT", "ts": ts, "nonce": nonce}))
        suggestions = ["9.5a — Worker UX", "9.5b — Auto-process", "9.5c — Plan details"]
        return _pa_json({"ok": True, "file": os.path.basename(p), "suggestions": suggestions})
    except Exception as e:
        return _pa_json({"ok": False, "err": str(e)}, 500)

def _pa_hard_ensure():
    app = _pa_get_app()
    if not app:
        return False
    try:
        have = {r.rule for r in app.url_map.iter_rules()}
    except Exception:
        have = set()
    try:
        if '/agent/recent' not in have:
            app.add_url_rule('/agent/recent', view_func=_pa_recent_view, methods=['GET'])
        if '/agent/next2' not in have:
            app.add_url_rule('/agent/next2', view_func=_pa_next2_view, methods=['GET','POST'])
        return True
    except Exception:
        return False

_ok = _pa_hard_ensure()
try:
    import threading, time as _t
    def _later():
        for _ in range(20):
            if _pa_hard_ensure():
                return
            _t.sleep(0.25)
    threading.Thread(target=_later, daemon=True).start()
except Exception:
    pass
# ==== END HARD_ENSURE_AGENT_RECENT_NEXT2_V3 ====
# ==== SCAN_BIND_AGENT_V4 ====
# Bind /agent/recent and /agent/next2 to *any* Flask app object present in globals().
try:
    import os, json, time, uuid, glob, threading
    from flask import Response
except Exception:
    pass

try:
    ROOT
except NameError:
    import os as _os
    ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), ".."))

def _pa_json(o, status=200):
    try:
        return Response(json.dumps(o), mimetype="application/json", status=status)
    except Exception:
        return Response('{"ok":false}', mimetype="application/json", status=500)

def _pa_approvals_dir():
    d = os.path.join(ROOT, 'tmp', 'phone', 'approvals')
    try:
        os.makedirs(d, exist_ok=True)
    except Exception:
        pass
    return d

def _pa_recent_view():
    try:
        d = _pa_approvals_dir()
        fs = sorted(glob.glob(os.path.join(d, 'approve_*.json')), key=os.path.getmtime, reverse=True)[:25]
        items = []
        for f in fs:
            try:
                items.append({"file": os.path.basename(f), "bytes": os.path.getsize(f)})
            except Exception:
                pass
        return _pa_json({"ok": True, "approvals": items})
    except Exception as e:
        return _pa_json({"ok": False, "err": str(e)}, 500)

def _pa_next2_view():
    try:
        d = _pa_approvals_dir()
        ts = int(time.time()); nonce = str(uuid.uuid4())
        p = os.path.join(d, f"approve_{ts}_{nonce}.json")
        with open(p, 'w', encoding='utf-8') as f:
            f.write(json.dumps({"ok": True, "action": "NEXT", "ts": ts, "nonce": nonce}))
        suggestions = ["9.5a — Worker UX", "9.5b — Auto-process", "9.5c — Plan details"]
        return _pa_json({"ok": True, "file": os.path.basename(p), "suggestions": suggestions})
    except Exception as e:
        return _pa_json({"ok": False, "err": str(e)}, 500)

def _pa_is_flask_app(obj):
    try:
        return hasattr(obj, "add_url_rule") and hasattr(obj, "url_map")
    except Exception:
        return False

def _pa_bind_to(app):
    try:
        have = {r.rule for r in app.url_map.iter_rules()}
    except Exception:
        have = set()
    try:
        if "/agent/recent" not in have:
            app.add_url_rule("/agent/recent", view_func=_pa_recent_view, methods=["GET"])
        if "/agent/next2" not in have:
            app.add_url_rule("/agent/next2", view_func=_pa_next2_view, methods=["GET","POST"])
        return True
    except Exception:
        return False

def _pa_scan_and_bind():
    ok = False
    try:
        for v in list(globals().values()):
            if _pa_is_flask_app(v):
                if _pa_bind_to(v):
                    ok = True
    except Exception:
        pass
    return ok

# Try now + retry for a few seconds while app objects appear.
def _pa_scan_loop():
    for _ in range(40):
        if _pa_scan_and_bind():
            return
        time.sleep(0.25)

try:
    _ = threading.Thread(target=_pa_scan_loop, daemon=True).start()
except Exception:
    pass
# ==== END SCAN_BIND_AGENT_V4 ====
# ==== FLASK_MONKEYPATCH_BIND_V1 ====
# Ensure /agent/recent and /agent/next2 attach to ANY Flask app constructed in this process.
try:
    import os, json, time, uuid, glob, threading
    import flask
    from flask import Flask, Response
    try:
        ROOT
    except NameError:
        ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    def _pa_json(o, status=200):
        try:
            return Response(json.dumps(o), mimetype="application/json", status=status)
        except Exception:
            return Response('{"ok":false}', mimetype="application/json", status=500)

    def _pa_approvals_dir():
        d = os.path.join(ROOT, 'tmp', 'phone', 'approvals')
        try: os.makedirs(d, exist_ok=True)
        except Exception: pass
        return d

    def _pa_recent_view():
        try:
            d = _pa_approvals_dir()
            fs = sorted(glob.glob(os.path.join(d, 'approve_*.json')), key=os.path.getmtime, reverse=True)[:25]
            items = []
            for f in fs:
                try: items.append({"file": os.path.basename(f), "bytes": os.path.getsize(f)})
                except Exception: pass
            return _pa_json({"ok": True, "approvals": items})
        except Exception as e:
            return _pa_json({"ok": False, "err": str(e)}, 500)

    def _pa_next2_view():
        try:
            d = _pa_approvals_dir()
            ts = int(time.time()); nonce = str(uuid.uuid4())
            p = os.path.join(d, f"approve_{ts}_{nonce}.json")
            with open(p, 'w', encoding='utf-8') as f:
                f.write(json.dumps({"ok": True, "action": "NEXT", "ts": ts, "nonce": nonce}))
            suggestions = ["9.5a — Worker UX", "9.5b — Auto-process", "9.5c — Plan details"]
            return _pa_json({"ok": True, "file": os.path.basename(p), "suggestions": suggestions})
        except Exception as e:
            return _pa_json({"ok": False, "err": str(e)}, 500)

    _PA_PENDING = [
        ("/agent/recent", _pa_recent_view, ("GET",)),
        ("/agent/next2",  _pa_next2_view,  ("GET","POST")),
    ]

    _orig_init = Flask.__init__
    def _init_patch(self, *a, **kw):
        _orig_init(self, *a, **kw)
        try: have = {r.rule for r in self.url_map.iter_rules()}
        except Exception: have = set()
        for rule, view, methods in list(_PA_PENDING):
            if rule not in have:
                try: self.add_url_rule(rule, view_func=view, methods=list(methods))
                except Exception: pass

    if not getattr(Flask, "__pa_bind_patch__", False):
        Flask.__init__ = _init_patch
        Flask.__pa_bind_patch__ = True

    def _bind_existing():
        try:
            for v in list(globals().values()):
                try:
                    if hasattr(v, "add_url_rule") and hasattr(v, "url_map"):
                        have = {r.rule for r in v.url_map.iter_rules()}
                        for rule, view, methods in _PA_PENDING:
                            if rule not in have:
                                try: v.add_url_rule(rule, view_func=view, methods=list(methods))
                                except Exception: pass
                except Exception:
                    pass
        except Exception:
            pass

    threading.Thread(target=_bind_existing, daemon=True).start()
except Exception:
    pass
# ==== END FLASK_MONKEYPATCH_BIND_V1 ====

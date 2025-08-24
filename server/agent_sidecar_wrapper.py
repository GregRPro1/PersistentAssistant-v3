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
    host = os.environ.get("PA_SIDECAR_HOST","127.0.0.1")
    port = int(os.environ.get("PA_SIDECAR_PORT","8782"))
    LOG("[wrapper]", SIG, "running on {}:{}".format(host, port))
    app.run(host=host, port=port, threaded=True, use_reloader=False)

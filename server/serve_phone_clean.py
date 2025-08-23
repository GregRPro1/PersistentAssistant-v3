from flask import Flask, request, jsonify, send_from_directory
import os, sys, time, json, ipaddress, threading, socket
SIG = "pa_diag_v2"
from server.phone_blueprint_agent_patch import register_phone_blueprint
ROOT = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(ROOT)
PWA_DIR = os.path.join(REPO, "web", "pwa")
APPROVALS_DIR = os.path.join(REPO, "tmp", "phone", "approvals")
STATE_DIR     = os.path.join(REPO, "tmp", "phone", "state")
os.makedirs(APPROVALS_DIR, exist_ok=True); os.makedirs(STATE_DIR, exist_ok=True); os.makedirs(PWA_DIR, exist_ok=True)
ALLOW = ["127.0.0.1/32","127.0.0.0/8","10.0.0.0/8","172.16.0.0/12","192.168.0.0/16","::1/128","fe80::/10","fc00::/7"]
TS_SKEW = 300; NONCE_TTL = 900; _lock = threading.Lock()
def load_token():
    t = os.getenv("PHONE_APPROVALS_TOKEN", "")
    try:
        p = os.path.join(REPO, "config", "phone_approvals.yaml")
        if os.path.exists(p):
            for ln in open(p,"r",encoding="utf-8"):
                s = ln.strip()
                if s.startswith("token:"):
                    v = s.split(":",1)[1].strip()
                    if v[:1] == "\"" and v[-1:] == "\"": v = v[1:-1]
                    if not t: t = v
                    break
    except Exception: pass
    return t
def allowed(remote):
    try: ip = ipaddress.ip_address(remote)
    except Exception: return False
    nets=[]
    for c in ALLOW:
        try: nets.append(ipaddress.ip_network(c, strict=False))
        except Exception: pass
    return any(ip in n for n in nets) if nets else True
def lan_ip():
    try:
        s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8",80)); ip=s.getsockname()[0]; s.close(); return ip
    except Exception: return "127.0.0.1"
app = Flask(__name__)
@app.route("/phone/ping", methods=["GET"])
def ping(): return jsonify({"ok":True,"t":int(time.time()),"sig":SIG})
@app.route("/phone/health", methods=["GET"])
def health(): return jsonify({"ok":True,"has_token":bool(load_token()),"sig":SIG})
@app.route("/__routes__", methods=["GET"])
def routes():
    rules = sorted([str(r) for r in app.url_map.iter_rules()])
    return jsonify({"routes":rules,"sig":SIG})
@app.route("/phone/approve", methods=["POST"])
def approve():
    token = load_token()
    auth = request.headers.get("Authorization","")
    if not auth.startswith("Bearer "): return jsonify({"error":"missing_bearer","sig":SIG}), 401
    client_tok = auth.split(" ",1)[1].strip()
    if not token: return jsonify({"error":"server_token_not_configured","sig":SIG}), 401
    if client_tok != token: return jsonify({"error":"bad_token","sig":SIG}), 401
    remote = request.remote_addr or ""
    if not allowed(remote): return jsonify({"error":"ip_not_allowed","ip":remote,"sig":SIG}), 401
    data = request.get_json(silent=True) or {}
    try: ts = int(data.get("timestamp",0))
    except Exception: ts = 0
    nonce = str(data.get("nonce","")).strip()
    now = int(time.time())
    if not (now-TS_SKEW <= ts <= now+TS_SKEW): return jsonify({"error":"timestamp_out_of_range","now":now,"ts":ts,"skew":TS_SKEW,"sig":SIG}), 400
    if len(nonce) < 8: return jsonify({"error":"bad_nonce","sig":SIG}), 400
    np = os.path.join(STATE_DIR, "nonces_diag.json")
    try:
        with _lock:
            try:
                seen = json.load(open(np,"r",encoding="utf-8"))
                if not isinstance(seen,dict): seen={}
            except Exception: seen={}
            cutoff = now - NONCE_TTL
            for k in list(seen.keys()):
                try:
                    if int(seen[k]) < cutoff: del seen[k]
                except Exception: del seen[k]
            if nonce in seen: return jsonify({"error":"replay","sig":SIG}), 409
            seen[nonce]=now
            open(np,"w",encoding="utf-8").write(json.dumps(seen))
    except Exception as e: return jsonify({"error":"nonce_store_failed","detail":str(e),"sig":SIG}), 500
    try:
        fn = os.path.join(APPROVALS_DIR, f"approve_{now}_{nonce}.json")
        open(fn,"w",encoding="utf-8").write(json.dumps({"action":data.get("action"),"data":data.get("data"),"timestamp":ts,"nonce":nonce}))
    except Exception as e: return jsonify({"error":"filedrop_failed","detail":str(e),"sig":SIG}), 500
    return jsonify({"ok":True,"nonce":nonce,"sig":SIG})
@app.route("/pwa/config", methods=["GET"])
def pwa_config():
    base = os.getenv("PA_APPROVALS_BASE", "http://127.0.0.1:8781")
    return jsonify({"approvals_base": base, "lan_hint": lan_ip(), "sig": SIG})
@app.route("/pwa/diag", methods=["GET"])
def pwa_diag():
    try: return send_from_directory(PWA_DIR, "diagnostics.html")
    except Exception: return jsonify({"error":"diag_not_found","path":PWA_DIR,"sig":SIG}), 404
if __name__ == "__main__":
    port = 8781
    try:
        if len(sys.argv) > 1: port = int(sys.argv[1])
    except Exception: pass
    app.run(host="0.0.0.0", port=port, debug=False)


# ==== PA_DIAG_PATCH_BEGIN (auto) ====
try:
    from flask import send_file, request, jsonify
except Exception:
    from flask import jsonify
    send_file = None
import os
ROOT = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(ROOT)
DIAG_HTML = os.path.join(REPO, 'web', 'pwa', 'diagnostics.html')
def _pa_diag_proxy():
    try:
        if send_file and os.path.isfile(DIAG_HTML):
            return send_file(DIAG_HTML)
        # minimal fallback:
        return '<!doctype html><h1>Diagnostics v2</h1><p>Missing diagnostics.html</p>'
    except Exception as e:
        return ('diag error: %s' % e), 500
def _pa_patch_diag_route(app):
    # replace existing /pwa/diag view func if present; else add rule
    replaced = False
    try:
        for rule in list(app.url_map.iter_rules()):
            if str(rule.rule) == '/pwa/diag':
                app.view_functions[rule.endpoint] = _pa_diag_proxy
                replaced = True
                break
    except Exception:
        pass
    if not replaced:
        try:
            app.add_url_rule('/pwa/diag', endpoint='pa_diag_proxy', view_func=_pa_diag_proxy)
        except Exception:
            pass
try:
    _pa_patch_diag_route(app)
except Exception:
    pass
# ==== PA_DIAG_PATCH_END ====


# ==== PA_DIAG_NOCACHE_BEGIN ====
try:
    @app.after_request
    def _pa_no_cache(resp):
        try:
            p = getattr(__import__('flask').request, 'path', '')
            if p == '/pwa/diag' or p.startswith('/pwa/config'):
                resp.headers['Cache-Control']='no-store, no-cache, must-revalidate, max-age=0'
        except Exception:
            pass
        return resp
except Exception:
    pass
# ==== PA_DIAG_NOCACHE_END ====

# ==== PA_PACKS_PATCH_BEGIN ====
try:
    from flask import jsonify, send_file, request
except Exception:
    from flask import jsonify, request
    send_file=None
import os, time
ROOT = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(ROOT)
PACKS_DIR = os.path.join(REPO, 'tmp', 'feedback')
def _packs_list():
    out=[]
    try:
        if os.path.isdir(PACKS_DIR):
            for n in sorted(os.listdir(PACKS_DIR)):
                p=os.path.join(PACKS_DIR,n)
                if os.path.isfile(p):
                    out.append({'name':n,'size':os.path.getsize(p),'mtime':int(os.path.getmtime(p))})
    except Exception as e:
        return jsonify({'ok':False,'error':str(e)})
    return jsonify({'ok':True,'packs':out})
def _packs_latest():
    try:
        items=[(n,os.path.getmtime(os.path.join(PACKS_DIR,n))) for n in os.listdir(PACKS_DIR)]
        items=[(n,t) for (n,t) in items if os.path.isfile(os.path.join(PACKS_DIR,n))]
        items.sort(key=lambda x: x[1], reverse=True)
        n=items[0][0] if items else None
        return jsonify({'ok':True,'latest':n})
    except Exception as e:
        return jsonify({'ok':False,'error':str(e)})
def _packs_download(name):
    try:
        p=os.path.join(PACKS_DIR,name)
        if send_file and os.path.isfile(p):
            return send_file(p, as_attachment=True)
    except Exception as e:
        return ('download error: %s' % e), 500
    return ('not found',404)
def _pa_patch_packs(app):
    try:
        app.add_url_rule('/packs/list', endpoint='packs_list', view_func=_packs_list, methods=['GET'])
        app.add_url_rule('/packs/latest', endpoint='packs_latest', view_func=_packs_latest, methods=['GET'])
        app.add_url_rule('/packs/download/<name>', endpoint='packs_download', view_func=_packs_download, methods=['GET'])
    except Exception:
        pass
try:
    _pa_patch_packs(app)
except Exception:
    pass
# ==== PA_PACKS_PATCH_END ====


# ==== PA_TOKEN_FIX_BEGIN ====
try:
    try:
        import yaml
        _pa_has_yaml=True
    except Exception:
        _pa_has_yaml=False
    import os
    def _pa_load_token2():
        try:
            p=os.path.join(REPO,'config','phone_approvals.yaml')
            s=open(p,'r',encoding='utf-8').read()
            # YAML path if available
            if _pa_has_yaml:
                try:
                    d=yaml.safe_load(s) or {}
                    val=d.get('token','')
                    if isinstance(val,str):
                        v=val.strip()
                        q=v[:1]
                        if q in (chr(34), chr(39)) and v.endswith(q):
                            v=v[1:-1]
                        return v
                except Exception:
                    pass
            # fallback: simple line parse
            for ln in s.splitlines():
                ls=ln.strip()
                if ls.startswith('token:'):
                    v=ls.split(':',1)[1].strip()
                    q=v[:1]
                    if q in (chr(34), chr(39)) and v.endswith(q):
                        v=v[1:-1]
                    return v
        except Exception:
            return ''
    _PA_TOKEN = _pa_load_token2()
    @app.route('/agent/reload_token', methods=['POST'])
    def _pa_reload_token():
        try:
            from flask import jsonify
            global _PA_TOKEN
            _PA_TOKEN = _pa_load_token2()
            return jsonify({'ok':True,'token_len': len(_PA_TOKEN)})
        except Exception as e:
            return ('error: %s' % e), 500
except Exception:
    pass
# ==== PA_TOKEN_FIX_END ====


# ==== PA_AGENT_PATCH_BEGIN ====
try:
    from flask import send_file, request, jsonify
except Exception:
    from flask import jsonify, request
    send_file=None
import os, time, json
ROOT = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(ROOT)
PWA_DIR = os.path.join(REPO, 'web', 'pwa')
APPROVALS_DIR = os.path.join(REPO, 'tmp', 'phone', 'approvals')
PACKS_DIR = os.path.join(REPO, 'tmp', 'feedback')
PLAN_PATH = None
for base,dirs,files in os.walk(REPO):
    if 'project_plan_v3.yaml' in files:
        PLAN_PATH = os.path.join(base,'project_plan_v3.yaml'); break
def _read_plan_summary():
    out={'active_step':None,'name':None,'desc':None,'next_ids':[]}
    try:
        import yaml
        if not PLAN_PATH: return out
        d=yaml.safe_load(open(PLAN_PATH,'r',encoding='utf-8').read()) or {}
        def alln(x):
            st=[x]; r=[]
            while st:
                v=st.pop()
                if isinstance(v,dict): r.append(v); st.extend(list(v.values()))
                elif isinstance(v,list): st.extend(v)
            return r
        def sid(n): return str(n.get('id') or n.get('step_id') or '')
        def parse_id(s):
            try: return [int(x) for x in str(s).split('.')]
            except: return []
        a=d.get('active_step'); out['active_step']=a
        cur=None
        for n in alln(d):
            if sid(n).lower()==str(a).lower(): cur=n; break
        if cur:
            out['name']=cur.get('name')
            out['desc']=cur.get('description') or cur.get('desc')
        ids=[]
        for n in alln(d):
            s=sid(n);
            if s: ids.append(s)
        curv=parse_id(a) if a else []
        nxt=[i for i in ids if parse_id(i)>curv]
        nxt=sorted(set(nxt), key=parse_id)[:5]
        out['next_ids']=nxt
    except Exception as e:
        out['error']=str(e)
    return out
@app.route('/pwa/agent', methods=['GET'])
def pa_agent_html():
    try:
        p=os.path.join(PWA_DIR,'agent.html')
        if send_file and os.path.isfile(p): return send_file(p)
    except Exception as e:
        return ('agent html error: %s' % e), 500
    return ('missing agent.html',404)
@app.route('/agent/summary', methods=['GET'])
def pa_agent_summary():
    la=None; lp=None
    try:
        la=max((n for n in os.listdir(APPROVALS_DIR)), key=lambda n: os.path.getmtime(os.path.join(APPROVALS_DIR,n))) if os.path.isdir(APPROVALS_DIR) else None
        lp=max((n for n in os.listdir(PACKS_DIR)), key=lambda n: os.path.getmtime(os.path.join(PACKS_DIR,n))) if os.path.isdir(PACKS_DIR) else None
    except Exception:
        pass
    return jsonify({'ok':True,'summary':dict(_read_plan_summary(), latest_approval=la, latest_pack=lp)})
@app.route('/agent/ask', methods=['POST'])
def pa_agent_ask():
    try:
        if not _auth_ok(request): return ('unauthorized',401)
        j=request.get_json(force=True) or {}
        text=str(j.get('text') or '').strip()
        if not text: return ('empty',400)
        ts=int(time.time()); nonce=str(j.get('nonce') or ts)
        os.makedirs(APPROVALS_DIR, exist_ok=True)
        name='approve_ask_{0}_{1}.json'.format(ts,nonce)
        open(os.path.join(APPROVALS_DIR,name),'w',encoding='utf-8').write(json.dumps({'action':'ASK','text':text,'timestamp':ts,'nonce':nonce,'source':'pwa'}))
        return jsonify({'ok':True,'file':name})
    except Exception as e:
        return ('error: %s' % e), 500
@app.route('/agent/choose', methods=['POST'])
def pa_agent_choose():
    try:
        if not _auth_ok(request): return ('unauthorized',401)
        j=request.get_json(force=True) or {}
        step=str(j.get('step_id') or '').strip()
        if not step: return ('empty',400)
        ts=int(time.time()); nonce=str(j.get('nonce') or ts)
        os.makedirs(APPROVALS_DIR, exist_ok=True)
        name='approve_set_active_{0}_{1}.json'.format(step.replace('/','_'),ts)
        open(os.path.join(APPROVALS_DIR,name),'w',encoding='utf-8').write(json.dumps({'action':'SET_ACTIVE_STEP','step_id':step,'timestamp':ts,'nonce':nonce,'source':'pwa'}))
        return jsonify({'ok':True,'file':name})
    except Exception as e:
        return ('error: %s' % e), 500
# ==== PA_AGENT_PATCH_END ====

# ==== PA_AGENT_INJECT_BEGIN ====
import os, time, json
try:
    from flask import request, jsonify, send_file
except Exception:
    from flask import request, jsonify
    send_file = None

ROOT = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(ROOT)
PWA_DIR = os.path.join(REPO, 'web', 'pwa')
APPROVALS_DIR = os.path.join(REPO, 'tmp', 'phone', 'approvals')
PACKS_DIR = os.path.join(REPO, 'tmp', 'feedback')

# Ensure _PA_TOKEN and _auth_ok exist
try:
    _PA_TOKEN
except NameError:
    _PA_TOKEN = ''
def _auth_ok(req):
    try:
        h = req.headers.get('Authorization','')
        if h.lower().startswith('bearer '):
            tok=h.split(' ',1)[1].strip()
            return bool(_PA_TOKEN) and tok==_PA_TOKEN
    except Exception:
        pass
    return False

# Small helpers
def _latest_name(path):
    try:
        items=[(n, os.path.getmtime(os.path.join(path,n))) for n in os.listdir(path)]
        items=[(n,t) for (n,t) in items if os.path.isfile(os.path.join(path,n))]
        items.sort(key=lambda x: x[1], reverse=True)
        return items[0][0] if items else None
    except Exception:
        return None

def _read_plan_summary():
    out={'active_step':None,'name':None,'desc':None,'next_ids':[]}
    try:
        import yaml
        # locate plan
        plan=None
        for base,dirs,files in os.walk(REPO):
            if 'project_plan_v3.yaml' in files:
                plan=os.path.join(base,'project_plan_v3.yaml'); break
        if not plan: return out
        d=yaml.safe_load(open(plan,'r',encoding='utf-8').read()) or {}
        def alln(x):
            st=[x]; r=[]
            while st:
                v=st.pop()
                if isinstance(v,dict): r.append(v); st.extend(list(v.values()))
                elif isinstance(v,list): st.extend(v)
            return r
        def sid(n): return str(n.get('id') or n.get('step_id') or '')
        def parse_id(s):
            try: return [int(x) for x in str(s).split('.')]
            except: return []
        a=d.get('active_step'); out['active_step']=a
        cur=None
        for n in alln(d):
            if sid(n).lower()==str(a).lower(): cur=n; break
        if cur:
            out['name']=cur.get('name')
            out['desc']=cur.get('description') or cur.get('desc')
        ids=[]
        for n in alln(d):
            s=sid(n)
            if s: ids.append(s)
        curv=parse_id(a) if a else []
        nxt=[i for i in ids if parse_id(i)>curv]
        nxt=sorted(set(nxt), key=parse_id)[:5]
        out['next_ids']=nxt
    except Exception as e:
        out['error']=str(e)
    return out

def _agent_html():
    try:
        p=os.path.join(PWA_DIR,'agent.html')
        if send_file and os.path.isfile(p): return send_file(p)
        return ('missing agent.html',404)
    except Exception as e:
        return ('agent html error: %s' % e), 500

def _agent_summary():
    return jsonify({'ok':True,'summary':dict(_read_plan_summary(),
                                            latest_approval=_latest_name(APPROVALS_DIR),
                                            latest_pack=_latest_name(PACKS_DIR))})

def _agent_ask():
    if not _auth_ok(request): return ('unauthorized',401)
    try:
        j=request.get_json(force=True) or {}
        text=str(j.get('text') or '').strip()
        if not text: return ('empty',400)
        ts=int(time.time()); nonce=str(j.get('nonce') or ts)
        os.makedirs(APPROVALS_DIR, exist_ok=True)
        name='approve_ask_{0}_{1}.json'.format(ts,nonce)
        open(os.path.join(APPROVALS_DIR,name),'w',encoding='utf-8').write(json.dumps(
            {'action':'ASK','text':text,'timestamp':ts,'nonce':nonce,'source':'pwa'}))
        return jsonify({'ok':True,'file':name})
    except Exception as e:
        return ('error: %s' % e), 500

def _agent_choose():
    if not _auth_ok(request): return ('unauthorized',401)
    try:
        j=request.get_json(force=True) or {}
        step=str(j.get('step_id') or '').strip()
        if not step: return ('empty',400)
        ts=int(time.time()); nonce=str(j.get('nonce') or ts)
        os.makedirs(APPROVALS_DIR, exist_ok=True)
        name='approve_set_active_{0}_{1}.json'.format(step.replace('/','_'),ts)
        open(os.path.join(APPROVALS_DIR,name),'w',encoding='utf-8').write(json.dumps(
            {'action':'SET_ACTIVE_STEP','step_id':step,'timestamp':ts,'nonce':nonce,'source':'pwa'}))
        return jsonify({'ok':True,'file':name})
    except Exception as e:
        return ('error: %s' % e), 500

def _pa_register_agent(app):
    # replace or add rules atomically
    try:
        # replace existing endpoints if present
        for rule in list(app.url_map.iter_rules()):
            if str(rule.rule) == '/pwa/agent':
                app.view_functions[rule.endpoint]=_agent_html
            if str(rule.rule) == '/agent/summary':
                app.view_functions[rule.endpoint]=_agent_summary
            if str(rule.rule) == '/agent/ask':
                app.view_functions[rule.endpoint]=_agent_ask
            if str(rule.rule) == '/agent/choose':
                app.view_functions[rule.endpoint]=_agent_choose
        # add if missing
        app.add_url_rule('/pwa/agent', endpoint='pa_agent_html', view_func=_agent_html, methods=['GET'])
        app.add_url_rule('/agent/summary', endpoint='pa_agent_summary', view_func=_agent_summary, methods=['GET'])
        app.add_url_rule('/agent/ask', endpoint='pa_agent_ask', view_func=_agent_ask, methods=['POST'])
        app.add_url_rule('/agent/choose', endpoint='pa_agent_choose', view_func=_agent_choose, methods=['POST'])
    except Exception:
        pass

try:
    _pa_register_agent(app)
except Exception:
    pass
# ==== PA_AGENT_INJECT_END ====

# ==== PA_AGENT_CALLS_BEGIN ====
try:
    from server.agent_injector import pa_register_agent as _pa_reg_agent
    _pa_reg_agent(app)
except Exception:
    pass
# ==== PA_AGENT_CALLS_END ====


from server.agent_bp import register_agent_bp

app = register_agent_bp(app)



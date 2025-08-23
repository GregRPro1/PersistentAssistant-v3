import os, time, json
from typing import Any
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

def _load_token() -> str:
    p = os.path.join(REPO,'config','phone_approvals.yaml')
    try:
        import yaml
        d = yaml.safe_load(open(p,'r',encoding='utf-8').read()) or {}
        v = d.get('token','')
        if isinstance(v,str):
            vv = v.strip()
            q = vv[:1]
            if q in (chr(34), chr(39)) and vv.endswith(q):
                vv = vv[1:-1]
            return vv
    except Exception:
        pass
    try:
        s = open(p,'r',encoding='utf-8').read()
        for ln in s.splitlines():
            ls = ln.strip()
            if ls.startswith('token:'):
                v = ls.split(':',1)[1].strip()
                q = v[:1]
                if q in (chr(34), chr(39)) and v.endswith(q):
                    v = v[1:-1]
                return v
    except Exception:
        pass
    return ''

_PA_TOKEN = _load_token()
def _auth_ok(req) -> bool:
    try:
        h = req.headers.get('Authorization','')
        if h.lower().startswith('bearer '):
            tok = h.split(' ',1)[1].strip()
            return bool(_PA_TOKEN) and tok == _PA_TOKEN
    except Exception:
        pass
    return False

def _latest_name(path:str):
    try:
        items = [(n, os.path.getmtime(os.path.join(path,n))) for n in os.listdir(path)]
        items = [(n,t) for (n,t) in items if os.path.isfile(os.path.join(path,n))]
        items.sort(key=lambda x: x[1], reverse=True)
        return items[0][0] if items else None
    except Exception:
        return None

def _read_plan_summary():
    out={'active_step':None,'name':None,'desc':None,'next_ids':[]}
    try:
        import yaml
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
            s=sid(n);
            if s: ids.append(s)
        curv=parse_id(a) if a else []
        nxt=[i for i in ids if parse_id(i)>curv]
        nxt=sorted(set(nxt), key=parse_id)[:5]
        out['next_ids']=nxt
    except Exception as e:
        out['error']=str(e)
    return out

def pa_register_agent(app:Any) -> None:
    # no-cache for agent page
    try:
        @app.after_request
        def _pa_nc(resp):
            try:
                pth=getattr(__import__('flask').request,'path','')
                if pth=='/pwa/agent':
                    resp.headers['Cache-Control']='no-store, no-cache, must-revalidate, max-age=0'
            except Exception: pass
            return resp
    except Exception: pass

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
            name='approve_set_active_{0}_{1}.json'.format(step.replace('/', '_'), ts)
            open(os.path.join(APPROVALS_DIR,name),'w',encoding='utf-8').write(json.dumps(
                {'action':'SET_ACTIVE_STEP','step_id':step,'timestamp':ts,'nonce':nonce,'source':'pwa'}))
            return jsonify({'ok':True,'file':name})
        except Exception as e:
            return ('error: %s' % e), 500

    # replace-or-add registration
    try:
        for rule in list(app.url_map.iter_rules()):
            if str(rule.rule) == '/pwa/agent': app.view_functions[rule.endpoint]=_agent_html
            if str(rule.rule) == '/agent/summary': app.view_functions[rule.endpoint]=_agent_summary
            if str(rule.rule) == '/agent/ask': app.view_functions[rule.endpoint]=_agent_ask
            if str(rule.rule) == '/agent/choose': app.view_functions[rule.endpoint]=_agent_choose
        app.add_url_rule('/pwa/agent', endpoint='pa_agent_html', view_func=_agent_html, methods=['GET'])
        app.add_url_rule('/agent/summary', endpoint='pa_agent_summary', view_func=_agent_summary, methods=['GET'])
        app.add_url_rule('/agent/ask', endpoint='pa_agent_ask', view_func=_agent_ask, methods=['POST'])
        app.add_url_rule('/agent/choose', endpoint='pa_agent_choose', view_func=_agent_choose, methods=['POST'])
    except Exception:
        pass


import os, time, json
from typing import Any
from flask import Flask, request, jsonify, send_file, make_response
app = Flask('agent_sidecar')
ROOT = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(ROOT)
PWA_DIR = os.path.join(REPO,'web','pwa')
APPROVALS_DIR = os.path.join(REPO,'tmp','phone','approvals')
PACKS_DIR = os.path.join(REPO,'tmp','feedback')
CFG = os.path.join(REPO,'config','phone_approvals.yaml')
try:
    import yaml
    _HAS_YAML=True
except Exception:
    _HAS_YAML=False
def _load_token()->str:
    try:
        if _HAS_YAML:
            d=yaml.safe_load(open(CFG,'r',encoding='utf-8').read()) or {}
            v=d.get('token','')
            if isinstance(v,str):
                vv=v.strip(); q=vv[:1]
                if q in (chr(34),chr(39)) and vv.endswith(q): vv=vv[1:-1]
                return vv
        s=open(CFG,'r',encoding='utf-8').read()
        for ln in s.splitlines():
            ls=ln.strip()
            if ls.startswith('token:'):
                v=ls.split(':',1)[1].strip(); q=v[:1]
                if q in (chr(34),chr(39)) and v.endswith(q): v=v[1:-1]
                return v
    except Exception: pass
    return ''
_PA_TOKEN=_load_token()
def _auth_ok(req)->bool:
    try:
        h=req.headers.get('Authorization','')
        if h.lower().startswith('bearer '):
            tok=h.split(' ',1)[1].strip()
            return bool(_PA_TOKEN) and tok==_PA_TOKEN
    except Exception: pass
    return False
def _latest_name(path:str):
    try:
        items=[(n,os.path.getmtime(os.path.join(path,n))) for n in os.listdir(path)]
        items=[(n,t) for (n,t) in items if os.path.isfile(os.path.join(path,n))]
        items.sort(key=lambda x:x[1], reverse=True)
        return items[0][0] if items else None
    except Exception: return None
def _read_plan_summary():
    out={'active_step':None,'name':None,'desc':None,'next_ids':[]}
    try:
        plan=None
        if _HAS_YAML:
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
@app.after_request
def _nc(resp):
    try:
        pth=getattr(request,'path','')
        if pth=='/pwa/agent':
            resp.headers['Cache-Control']='no-store, no-cache, must-revalidate, max-age=0'
    except Exception: pass
    return resp
@app.route('/__routes__')
def _routes():
    return jsonify({'routes':[str(r.rule) for r in app.url_map.iter_rules()]})
@app.route('/pwa/agent')
def agent_html():
    p=os.path.join(PWA_DIR,'agent.html')
    if os.path.isfile(p):
        return make_response(send_file(p))
    return ('missing agent.html',404)
@app.route('/agent/summary')
def agent_summary():
    return jsonify({'ok':True,'summary':dict(_read_plan_summary(), latest_approval=_latest_name(APPROVALS_DIR), latest_pack=_latest_name(PACKS_DIR))})
@app.route('/agent/ask', methods=['POST'])
def agent_ask():
    if not _auth_ok(request): return ('unauthorized',401)
    j=request.get_json(force=True) or {}
    text=str(j.get('text') or '').strip()
    if not text: return ('empty',400)
    ts=int(time.time()); nonce=str(j.get('nonce') or ts)
    os.makedirs(APPROVALS_DIR, exist_ok=True)
    name='approve_ask_{0}_{1}.json'.format(ts,nonce)
    open(os.path.join(APPROVALS_DIR,name),'w',encoding='utf-8').write(json.dumps({'action':'ASK','text':text,'timestamp':ts,'nonce':nonce,'source':'pwa'}))
    return jsonify({'ok':True,'file':name})
@app.route('/agent/choose', methods=['POST'])
def agent_choose():
    if not _auth_ok(request): return ('unauthorized',401)
    j=request.get_json(force=True) or {}
    step=str(j.get('step_id') or '').strip()
    if not step: return ('empty',400)
    ts=int(time.time()); nonce=str(j.get('nonce') or ts)
    os.makedirs(APPROVALS_DIR, exist_ok=True)
    name='approve_set_active_{0}_{1}.json'.format(step.replace('/', '_'), ts)
    open(os.path.join(APPROVALS_DIR,name),'w',encoding='utf-8').write(json.dumps({'action':'SET_ACTIVE_STEP','step_id':step,'timestamp':ts,'nonce':nonce,'source':'pwa'}))
    return jsonify({'ok':True,'file':name})

@app.route('/agent/next', methods=['POST'])
def agent_next():
    if not _auth_ok(request): return ('unauthorized',401)
    j=request.get_json(force=True) or {}
    ts=int(time.time()); nonce=str(j.get('nonce') or ts)
    os.makedirs(APPROVALS_DIR, exist_ok=True)
    name='approve_{0}_{1}.json'.format(ts,nonce)
    open(os.path.join(APPROVALS_DIR,name),'w',encoding='utf-8').write(json.dumps({'action':'APPROVE_NEXT','data':None,'timestamp':ts,'nonce':nonce,'source':'pwa'}))
    return jsonify({'ok':True,'file':name})


def _set_active_step(step:str)->bool:
    try:
        import yaml, os
        plan=None
        for base,dirs,files in os.walk(REPO):
            if 'project_plan_v3.yaml' in files:
                plan=os.path.join(base,'project_plan_v3.yaml'); break
        if not plan: return False
        d=yaml.safe_load(open(plan,'r',encoding='utf-8').read()) or {}
        d['active_step']=step
        open(plan,'w',encoding='utf-8').write(yaml.safe_dump(d,sort_keys=False,allow_unicode=True))
        return True
    except Exception:
        return False

def _process_approvals():
    os.makedirs(APPROVALS_DIR, exist_ok=True)
    done=os.path.join(REPO,'tmp','phone','processed')
    os.makedirs(done, exist_ok=True)
    notes_dir=os.path.join(REPO,'tmp','notes'); os.makedirs(notes_dir, exist_ok=True)
    notes=os.path.join(notes_dir,'notes.md')
    out=[]
    def _json_or_none(p):
        try: return json.load(open(p,'r',encoding='utf-8'))
        except Exception: return None
    files=sorted([n for n in os.listdir(APPROVALS_DIR) if n.endswith('.json')], key=lambda n: os.path.getmtime(os.path.join(APPROVALS_DIR,n)))
    for name in files:
        p=os.path.join(APPROVALS_DIR,name)
        j=_json_or_none(p) or {}
        act=str(j.get('action') or '')
        rec={'file':name,'action':act,'ok':True}
        try:
            if act=='SET_ACTIVE_STEP':
                step=str(j.get('step_id') or '').strip()
                rec['ok']=bool(step) and _set_active_step(step)
            elif act=='ASK':
                text=str(j.get('text') or '').strip()
                ts=j.get('timestamp') or int(time.time())
                with open(notes,'a',encoding='utf-8') as f:
                    f.write('### ASK {0}\\n\\n{1}\\n\\n'.format(ts,text))
                rec['ok']=True
            else:
                rec['ok']=True
        except Exception as e:
            rec['ok']=False; rec['err']=str(e)
        out.append(rec)
        try: os.replace(p, os.path.join(done,name))
        except Exception: pass
    return out

@app.route('/agent/process', methods=['POST'])
def agent_process():
    if not _auth_ok(request): return ('unauthorized',401)
    res=_process_approvals()
    return jsonify({'ok':True,'processed':res})


def _next_suggestions():
    s=_read_plan_summary()
    su=[]
    try:
        nxt=(s.get('next_ids') or [])[:3]
        for sid in nxt:
            su.append({'id':sid,'title':'Go to '+sid,'kind':'step'})
    except Exception: pass
    su.append({'id':'ASK','title':'Ask the assistant','kind':'action'})
    return s,su

@app.route('/agent/next2', methods=['POST'])
def agent_next2():
    if not _auth_ok(request): return ('unauthorized',401)
    j=request.get_json(force=True) or {}
    ts=int(time.time()); nonce=str(j.get('nonce') or ts)
    os.makedirs(APPROVALS_DIR, exist_ok=True)
    name='approve_{0}_{1}.json'.format(ts,nonce)
    open(os.path.join(APPROVALS_DIR,name),'w',encoding='utf-8').write(json.dumps({'action':'APPROVE_NEXT','data':None,'timestamp':ts,'nonce':nonce,'source':'pwa'}))
    s,su=_next_suggestions()
    return jsonify({'ok':True,'file':name,'summary':s,'suggestions':su})


def _recent(n:int=5):
    try:
        appr_dir = APPROVALS_DIR
        files = []
        if os.path.isdir(appr_dir):
            for nm in os.listdir(appr_dir):
                p = os.path.join(appr_dir, nm)
                if os.path.isfile(p) and nm.endswith('.json'):
                    files.append((nm, os.path.getmtime(p)))
        files.sort(key=lambda x: x[1], reverse=True)
        files = [f for f,_ in files[:max(1,n)]]
    except Exception:
        files = []
    # notes tail
    notes_path = os.path.join(REPO,'tmp','notes','notes.md')
    notes_tail = ''
    notes_len = 0
    try:
        if os.path.isfile(notes_path):
            s = open(notes_path,'r',encoding='utf-8').read()
            notes_len = len(s)
            # last ~500 chars for quick view
            notes_tail = s[-500:] if len(s) > 500 else s
    except Exception:
        pass
    return {'approvals': files, 'notes_len': notes_len, 'notes_tail': notes_tail}

@app.route('/agent/recent')
def agent_recent():
    return jsonify({'ok': True, 'recent': _recent(), 'summary': _read_plan_summary()})


def _notes_path():
    return os.path.join(REPO,'tmp','notes','notes.md')

@app.route('/agent/notes', methods=['GET'])
def agent_notes_get():
    p=_notes_path(); os.makedirs(os.path.dirname(p), exist_ok=True)
    s=''
    try:
        if os.path.isfile(p): s=open(p,'r',encoding='utf-8').read()
    except Exception: pass
    return jsonify({'ok':True,'len':len(s),'text':s})

@app.route('/agent/notes', methods=['POST'])
def agent_notes_set():
    if not _auth_ok(request): return ('unauthorized',401)
    j=request.get_json(force=True) or {}
    mode=str(j.get('mode') or 'set')
    text=str(j.get('text') or '')
    p=_notes_path(); os.makedirs(os.path.dirname(p), exist_ok=True)
    try:
        if mode=='append':
            with open(p,'a',encoding='utf-8') as f:
                if text and not text.endswith('\\n'): text=text+'\\n'
                f.write(text)
        else:
            with open(p,'w',encoding='utf-8') as f: f.write(text)
        return jsonify({'ok':True})
    except Exception as e:
        return ('error: %s' % e, 500)

def _make_brief_pack():
    try:
        import zipfile
        ts=int(time.time())
        os.makedirs(PACKS_DIR, exist_ok=True)
        base=os.path.join(PACKS_DIR, 'brief_{0}.zip'.format(ts))
        summary=_read_plan_summary()
        recent=_recent() if ' _recent' in globals() or '_recent' in locals() else {'approvals':[],'notes_len':0,'notes_tail':''}
        notes=_notes_path()
        with zipfile.ZipFile(base,'w',compression=zipfile.ZIP_DEFLATED) as z:
            z.writestr('summary.json', json.dumps({'summary':summary,'recent':recent}, ensure_ascii=False, indent=2))
            if os.path.isfile(notes): z.write(notes, arcname='notes/notes.md')
        return base
    except Exception:
        return None

@app.route('/agent/brief', methods=['POST'])
def agent_brief():
    if not _auth_ok(request): return ('unauthorized',401)
    p=_make_brief_pack()
    if not p: return ('error creating brief', 500)
    return jsonify({'ok':True,'file':os.path.basename(p)})

def _collect_steps_from_yaml(doc):
    def all_nodes(x):
        st=[x]; out=[]
        while st:
            v=st.pop()
            if isinstance(v,dict): out.append(v); st.extend(list(v.values()))
            elif isinstance(v,list): st.extend(v)
        return out
    items=[]
    try:
        for n in all_nodes(doc):
            if not isinstance(n,dict): continue
            _id=str(n.get('id') or n.get('step_id') or '').strip()
            if not _id: continue
            title=str(n.get('name') or n.get('title') or n.get('desc') or '').strip()
            status=str(n.get('status') or n.get('state') or '').strip().lower()
            items.append({'id':_id,'title':title,'status':status})
    except Exception:
        pass
    return items

def _group_tree_by_major(steps):
    # '7.5b' -> major '7', child '5b'; '9.1' -> '9'/'1'
    tree={}
    for s in steps:
        _id=s.get('id','')
        if '.' in _id:
            major=_id.split('.',1)[0]
            minor=_id.split('.',1)[1]
        else:
            major=_id; minor=''
        g=tree.setdefault(major,[])
        g.append({'id':_id,'minor':minor,'title':s.get('title',''),'status':s.get('status','')})
    # sort minors semantically
    for k in tree:
        tree[k].sort(key=lambda x: x['id'])
    # build structured list
    out=[]
    for major in sorted(tree.keys(), key=lambda x: (len(x), x)):
        out.append({'id':str(major),'title':'Phase '+str(major),'status':'',
                    'children':[{'id':e['id'],'title':e['title'],'status':e['status']} for e in tree[major]]})
    return out

def _plan_tree():
    try:
        import yaml
        plan=None
        for base,dirs,files in os.walk(REPO):
            if 'project_plan_v3.yaml' in files:
                plan=os.path.join(base,'project_plan_v3.yaml'); break
        if not plan: return {'active':None,'tree':[]}
        doc=yaml.safe_load(open(plan,'r',encoding='utf-8').read()) or {}
        steps=_collect_steps_from_yaml(doc)
        tree=_group_tree_by_major(steps)
        return {'active':doc.get('active_step'),'tree':tree}
    except Exception:
        return {'active':None,'tree':[]}

@app.route('/agent/plan')
def agent_plan():
    return jsonify({'ok':True,'plan':_plan_tree()})

if __name__=='__main__':
    app.run(host='0.0.0.0', port=8782, debug=False)







# server/mobile_home.py
from flask import Blueprint, Response
from string import Template

bp = Blueprint('mobile_home', __name__)
mount_path = '/app'

_TPL = Template("""<!doctype html>
<html><head><meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>PA Mobile</title>
  <style>
    body{font-family:system-ui,Segoe UI,Arial,sans-serif;margin:16px}
    h1{font-size:20px;margin:6px 0 12px}
    input,button,textarea{font-size:16px}
    .btn{display:block;width:100%;padding:10px;margin:6px 0;background:#0a75ff;color:white;border:none;border-radius:8px;text-align:center;text-decoration:none}
    .row{display:flex;gap:8px} .row>div{flex:1}
    .card{background:#f7f7f7;padding:10px;border-radius:10px;margin-top:10px}
    pre{white-space:pre-wrap;font-family:ui-monospace,Consolas,monospace;background:#fff;padding:8px;border-radius:8px}
    .ok{color:green}.err{color:#b00}
  </style>
</head><body>
  <h1>Persistent Assistant — Mobile Console</h1>

  <div class="card">
    <h3>Apply pack</h3>
    <label>Direct ZIP URL
      <input id="direct" type="text" placeholder="https://.../PA_OUTPUT_*.zip">
    </label>
    <div class="row">
      <div><label>Repo<input id="repo" type="text" value="$REPO"></label></div>
      <div><label>Release<input id="rel" type="text" value="$REL"></label></div>
    </div>
    <label>Asset glob<input id="glob" type="text" value="$GLOB"></label>
    <label>GitHub token (optional)<input id="tok" type="text" value=""></label>
    <button class="btn" onclick="startApply()">Apply</button>
  </div>

  <div id="job" class="card" style="display:none">
    <div>Job: <code id="jid"></code> — <span id="jst">starting...</span></div>
    <pre id="log" style="min-height:180px"></pre>
  </div>

  <script>
    const MOUNT = '/api/jobs';
    function el(id){return document.getElementById(id)}
    async function startApply(){
      const payload = {
        direct_url: el('direct').value.trim(),
        repo: el('repo').value.trim(),
        release: el('rel').value.trim(),
        asset_glob: el('glob').value.trim(),
        gh_token: el('tok').value.trim(),
      };
      let res = await fetch(MOUNT + '/apply', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)});
      if(!res.ok){ alert('apply failed'); return; }
      let j = await res.json();
      el('job').style.display='block'; el('jid').textContent=j.id; el('jst').textContent=j.status;
      poll(j.id);
    }
    async function poll(id){
      try{
        let s = await fetch(`${MOUNT}/${id}`); if(s.ok){ let js = await s.json(); el('jst').textContent=js.status; }
      }catch(e){}
      try{
        let t = await fetch(`${MOUNT}/${id}/tail?n=400`); if(t.ok){ el('log').textContent = await t.text(); }
      }catch(e){}
      setTimeout(()=>poll(id), 1000);
    }
  </script>

  <div class="card">
    <a class="btn" href="/control/">Open full control</a>
    <div class="row">
      <a class="btn" style="background:#555" href="/ops/">Ops</a>
      <a class="btn" style="background:#777" href="/smoke/">Smoke</a>
    </div>
  </div>
</body></html>""")

def _page():
    return _TPL.substitute(REPO='GregRPro1/PersistentAssistant-v3', REL='PA-OUTPUT', GLOB='PA_OUTPUT_*.zip')

@bp.get('/')
def home():
    return Response(_page(), mimetype='text/html')

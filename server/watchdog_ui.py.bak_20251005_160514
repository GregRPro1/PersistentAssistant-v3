from flask import Blueprint, Response

bp = Blueprint('watchdog_ui', __name__, url_prefix='/app')

_HTML = r"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>PA Watchdog</title>
  <style>
    body{font-family:system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif;margin:16px;background:#0b0d10;color:#e8eef3}
    .card{background:#12161b;border:1px solid #202833;border-radius:14px;padding:16px;margin:0 auto;max-width:980px;box-shadow:0 1px 8px rgba(0,0,0,.25)}
    .row{display:flex;gap:12px;flex-wrap:wrap}
    .pill{display:inline-flex;align-items:center;gap:8px;border-radius:999px;padding:6px 10px;border:1px solid #243040;background:#0e1318}
    .dot{width:10px;height:10px;border-radius:50%}
    .dot.green{background:#21c55d}.dot.amber{background:#f59e0b}.dot.red{background:#ef4444}.dot.gray{background:#6b7280}.dot.blue{background:#3b82f6}
    button{background:#1f2937;color:#e8eef3;border:1px solid #263142;border-radius:10px;padding:6px 10px;cursor:pointer}
    button:hover{background:#263142}
    pre{background:#0e1318;border:1px solid #202833;border-radius:10px;padding:10px;max-height:220px;overflow:auto}
    .muted{color:#9aa7b2}
    .grid{display:grid;grid-template-columns:1.2fr .8fr auto auto;gap:10px;align-items:center}
    @media (max-width:740px){.grid{grid-template-columns:1fr} button{width:100%}}
  </style>
</head>
<body>
<div class="card">
  <h2>Watchdog Status</h2>
  <div id="summary" class="muted">loading…</div>
  <div id="tunnel" class="muted" style="margin:8px 0 14px 0;"></div>
  <div id="procs"></div>
</div>
<script>
const $ = (q)=>document.querySelector(q);
const el = (t,cls,txt)=>{ const e=document.createElement(t); if(cls) e.className=cls; if(txt!=null) e.textContent=txt; return e; };

function light(state){
  const m = {healthy:'green', starting:'amber', degraded:'amber', failed:'red', stopped:'gray', running:'blue'};
  return m[state]||'gray';
}

async function api(path, opts){
  const r = await fetch(path, opts||{});
  if(!r.ok) throw new Error(await r.text());
  return r.json();
}

function render(st){
  const age = st._file_age_s!=null ? `updated ${Math.round(st._file_age_s)}s ago` : '';
  $("#summary").textContent = `ok: ${st.ok} ${age}`;
  let t = '';
  try {
    const proc = st.processes?.tunnel;
    if(proc && proc.state==='healthy'){
      t = 'Tunnel healthy — see reports/ops/tunnel_url.txt';
    } else {
      t = 'Tunnel: ' + (proc?proc.state:'n/a');
    }
  } catch(e) {}
  $("#tunnel").textContent = t;

  const wrap = el('div','grid');
  for (const [name,p] of Object.entries(st.processes||{})){
    const pill = el('div','pill');
    const dot = el('span','dot '+light(p.state)); pill.appendChild(dot);
    pill.appendChild(el('span','',name+' '));
    pill.appendChild(el('span','muted',`#${p.pid||'—'}`));
    wrap.appendChild(pill);

    wrap.appendChild(el('div','muted',p.state));
    wrap.appendChild(el('div','muted','restarts: '+(p.restarts||0)));

    const actions = el('div','row');
    const btnR = el('button','', 'Restart');
    btnR.onclick = async ()=>{
      btnR.disabled=true; btnR.textContent='Restarting…';
      try { await api(`/watchdog/${name}/restart`, {method:'POST'}); } catch(e){ console.error(e); }
      finally { setTimeout(()=>{ btnR.disabled=false; btnR.textContent='Restart'; },1200); }
    };
    actions.appendChild(btnR);
    wrap.appendChild(actions);

    const logBox = el('div','',null);
    const pre = el('pre','muted','logs loading…');
    logBox.appendChild(pre);
    wrap.appendChild(logBox);
    api(`/watchdog/logs/${name}?tail=60`).then(j=>{
      pre.textContent = (j.stdout_tail||[]).join('\\n') + '\\n' + (j.stderr_tail||[]).join('\\n');
    }).catch(_=>{ pre.textContent='(no logs)'; });
  }
  $("#procs").innerHTML=''; $("#procs").appendChild(wrap);
}

async function tick(){
  try {
    const st = await api('/watchdog');
    render(st);
  } catch(e){ console.error(e); }
}
tick();
setInterval(tick, 2000);

const exitBtn = el('button','', 'Exit Watchdog'); 
exitBtn.style.cssText = 'position:fixed; top:12px; right:12px;';
exitBtn.onclick = async ()=>{ try{ await api('/watchdog/exit',{method:'POST'}) }catch(e){} };
document.body.appendChild(exitBtn);
</script>
</body>
</html>"""

@bp.get('/app/watchdog')
def watchdog_page():
    return Response(_HTML, mimetype='text/html')






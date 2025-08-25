/* Agent EXT v2 (tab-integrated) */
(function(){
  const Q  = (s, r=document)=>r.querySelector(s);
  const QA = (s, r=document)=>Array.from(r.querySelectorAll(s));
  function GET(path){
    const h = {cache:'no-store',headers:{}};
    try{ if(window.tok && window.tok.trim()){ h.headers.Authorization='Bearer '+window.tok.trim(); } }catch(e){}
    return fetch(path, h);
  }
  function badge(status){
    const s=(status||"").toLowerCase();
    if(s==="done") return '<span class="pa2-badge b-done">done</span>';
    if(["in_progress","active","working","running"].includes(s)) return '<span class="pa2-badge b-prog">in-progress</span>';
    if(["blocked","error","fail","failed"].includes(s)) return '<span class="pa2-badge b-blk">blocked</span>';
    return '<span class="pa2-badge b-todo">todo</span>';
  }
  function renderTree(nodes){
    const r=(arr)=>'<ul>'+arr.map(n=>(
      '<li><strong>'+ (n.id||'') +'</strong>'
      + (n.title? ' — '+String(n.title).replace(/[<>&]/g,'') : '')
      + ' '+badge(n.status)
      + (n.children && n.children.length? r(n.children) : '')
      + '</li>'
    )).join('')+'</ul>';
    return r(nodes||[]);
  }
  function findPlanContainer(){
    // Prefer an element that clearly belongs to the Plan tab/panel.
    let el = Q('#planPanel') || Q('#tab-plan') || Q('[data-tab="Plan"]') || Q('[aria-controls="plan"]');
    if(el && el.tagName==='A'){ const id = el.getAttribute('href')||el.getAttribute('aria-controls'); if(id){ const t=id.replace(/^#/,''); el = Q('#'+t) || el; } }
    if(!el){
      // Heuristic: section with heading containing "Plan"
      const candidates = QA('section,div');
      for(const c of candidates){
        const h = Q('h2,h3,h4', c);
        if(h && /plan/i.test(h.textContent||'')) return c;
      }
    }
    return el || document.body;
  }
  function mount(){
    // Inject status bar near top (but inside main content)
    let hostTop = Q('#agentHeader') || Q('main') || Q('.container') || document.body;
    if(!Q('#pa2Bar')){
      const bar = document.createElement('div');
      bar.id='pa2Bar'; bar.className='pa2-bar'; bar.style.display='none';
      bar.innerHTML = '<span id="pa2Status" class="pa2-pill">agent: …</span>'
                    + '<span id="pa2Totals" class="pa2-pill">totals: …</span>'
                    + '<span id="pa2Worker" class="pa2-pill">worker: …</span>'
                    + '<span id="pa2Approvals" class="pa2-pill">approvals: …</span>';
      hostTop.prepend(bar);
    }
    // Inject Plan panel inside Plan tab
    const planHost = findPlanContainer();
    if(planHost && !Q('#pa2Plan', planHost)){
      const panel = document.createElement('div');
      panel.id='pa2Plan'; panel.className='pa2-panel';
      const title = document.createElement('div');
      title.className='preline';
      title.textContent='Plan overview';
      const tree = document.createElement('div'); tree.className='pa2-tree'; tree.id='pa2Tree';
      panel.appendChild(tree);
      // Append near the top of plan section
      planHost.appendChild(panel);
    }
  }
  async function refresh(){
    try{
      const [pl, ws, ac] = await Promise.all([
        GET('/agent/plan'), GET('/agent/worker_status'), GET('/agent/approvals_count')
      ]);
      const ok = pl.ok && ws.ok && ac.ok;
      const bar = Q('#pa2Bar'); if(bar) bar.style.display='flex';
      const st = Q('#pa2Status'); if(st) st.textContent = 'agent: '+(ok?'OK':'…');
      let tree=[], totals={done:0,in_progress:0,blocked:0,todo:0};
      if(pl.ok){ const j=await pl.json(); tree=j.plan?.tree||[]; totals=j.plan?.totals||totals; }
      const tt = Q('#pa2Totals'); if(tt) tt.textContent = `totals: ✓${totals.done||0} • ▶︎${totals.in_progress||0} • !${totals.blocked||0} • ○${totals.todo||0}`;
      let worker='calls 0 · tok 0/0 · $0.0000';
      if(ws.ok){ const j=await ws.json(); const w=j.worker||{}; worker=`calls ${w.calls||0} · tok ${(w.tokens_in||0)}/${(w.tokens_out||0)} · $${(w.cost_usd||0).toFixed(4)}`; }
      const wk = Q('#pa2Worker'); if(wk) wk.textContent = worker;
      let approvals='0 files';
      if(ac.ok){ const j=await ac.json(); approvals=`${j.count||0} files`; }
      const ap = Q('#pa2Approvals'); if(ap) ap.textContent = 'approvals: '+approvals;
      const treeDiv = Q('#pa2Tree'); if(treeDiv) treeDiv.innerHTML = renderTree(tree);
    }catch(e){}
  }
  document.addEventListener('DOMContentLoaded', ()=>{ try{ mount(); refresh(); setInterval(refresh, 5000); }catch(e){} });
})();
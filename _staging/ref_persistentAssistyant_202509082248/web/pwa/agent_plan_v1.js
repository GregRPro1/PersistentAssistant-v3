(function(){
  function Q(s,r=document){return (r||document).querySelector(s)}
  function QA(s,r=document){return Array.from((r||document).querySelectorAll(s))}
  function bearer(){ try{ const t=localStorage.getItem("pa.token"); return t?t.trim():""; }catch(e){ return "" } }
  function H(){ const h={}; const t=bearer(); if(t) h["Authorization"]="Bearer "+t; return h; }
  async function jget(url){ const r=await fetch(url,{headers:H(),cache:"no-store"}); return r.ok?await r.json():null }
  function esc(s){ return String(s==null?"":s).replace(/[&<>]/g, c=>({ "&":"&amp;","<":"&lt;",">":"&gt;" }[c])) }
  function nodeTitle(n){ return esc(n.title||n.name||n.id||n.step_id||"untitled") }
  function badge(n){ const s=(n.status||n.state||"").toString().toLowerCase();
    const m={done:"🟢", ok:"🟢", "in-progress":"🟡", working:"🟡", planned:"⚪", todo:"⚪", blocked:"🔴", error:"🔴"};
    return m[s]||"⚪"; }
  function renderNode(n){
    const kids = Array.isArray(n.children)?n.children:[];
    const meta = [];
    ["id","step_id","status","state","phase"].forEach(k=>{ if(n[k]!=null){ meta.push(`<code>${esc(k)}=${esc(n[k])}</code>`)} });
    const head = `<summary>${badge(n)} ${nodeTitle(n)} ${meta.length?("<small>"+meta.join(" ")+"</small>"):""}</summary>`;
    if(!kids.length){ return `<details class="pa-node">${head}</details>` }
    return `<details class="pa-node"><summary>${badge(n)} ${nodeTitle(n)} ${meta.length?("<small>"+meta.join(" ")+"</small>"):""}</summary><div class="pa-children">` + kids.map(renderNode).join("") + `</div></details>`;
  }
  function renderTree(tree){
    if(!Array.isArray(tree)||!tree.length) return "<em>No plan data</em>";
    return `<div class="pa-tree">` + tree.map(renderNode).join("") + `</div>`;
  }
  async function refreshPlan(){
    const p = QA("h1,h2,h3,h4,h5").find(h=>/^\s*plan\s*$/i.test(h.textContent||"")); if(!p) return;
    const host = p.closest("section,div")||document.body; let box = Q("#paTree",host); if(!box){ box=document.createElement("div"); box.id="paTree"; box.style.maxHeight="50vh"; box.style.overflow="auto"; box.style.padding="8px"; box.style.border="1px solid #334155"; box.style.borderRadius="8px"; host.appendChild(box); }
    try{ const j=await jget("/agent/plan"); if(j && j.plan){ box.innerHTML = renderTree(j.plan.tree||[]); } else { box.innerHTML="<em>Plan unavailable</em>"; } }catch(e){ box.innerHTML="<em>Plan error</em>"; }
  }
  document.addEventListener("DOMContentLoaded", ()=>{ refreshPlan(); setInterval(refreshPlan, 7000); });
})();

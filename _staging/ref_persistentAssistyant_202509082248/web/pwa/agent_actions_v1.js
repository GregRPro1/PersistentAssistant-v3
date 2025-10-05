(function(){
  const Q=(s,r=document)=>r.querySelector(s); const QA=(s,r=document)=>Array.from((r||document).querySelectorAll(s));
  function bearer(){ try{ if(window.tok) return (""+window.tok).trim(); const t=localStorage.getItem("pa.token"); return t?t.trim():""; }catch(e){ return ""; } }
  function H(){ const h={}; const t=bearer(); if(t) h["Authorization"]="Bearer "+t; return h; }
  async function jget(url){ const r=await fetch(url,{headers:H(),cache:"no-store"}); let j=null; try{ j=r.ok?await r.json():null }catch(e){}; return {ok:r.ok,status:r.status,j} }
  function ensureBox(panel){ let box = Q(".pa-out", panel); if(!box){ box=document.createElement("pre"); box.className="pa-out"; panel.appendChild(box); } return box; }
  function log(panel, msg){ const box=ensureBox(panel); const t = "["+new Date().toLocaleTimeString()+"] "+msg+"\n"; box.textContent += t; box.scrollTop = box.scrollHeight; }
  function findPanelByHeading(name){ const hs=QA("h1,h2,h3,h4,h5"); for(const h of hs){ if((h.textContent||"").trim().toLowerCase()===name.toLowerCase()){ return h.closest("section,div")||h.parentElement; } } return null; }
  function pretty(obj){ try{ return JSON.stringify(obj,null,2) }catch(e){ return String(obj) } }
  async function doSummary(){ const p=findPanelByHeading("Summary"); if(!p) return; const r=await jget("/agent/summary"); log(p,"summary "+r.status+" "+(r.ok?"ok":"fail"));
    if(r.j){ let tgt=Q("#paSummaryJson",p); if(!tgt){ tgt=document.createElement("pre"); tgt.id="paSummaryJson"; tgt.style.whiteSpace="pre-wrap"; p.appendChild(tgt); }
      tgt.textContent = pretty(r.j); } }
  async function doPlan(){ const p=findPanelByHeading("Plan"); if(!p) return; const r=await jget("/agent/plan"); log(p,"plan "+r.status+" "+(r.ok?"ok":"fail"));
    if(r.j){ let tgt=Q("#paPlanJson",p); if(!tgt){ tgt=document.createElement("pre"); tgt.id="paPlanJson"; tgt.style.whiteSpace="pre-wrap"; tgt.style.display="none"; p.appendChild(tgt); }
      tgt.textContent = pretty(r.j); } }
  async function doRecent(){ const p=findPanelByHeading("Recent"); if(!p) return; const r=await jget("/agent/recent"); log(p,"recent "+r.status+" "+(r.ok?"ok":"fail")); if(r.j){ log(p, pretty(r.j)); } }
  async function doNext(){ const p=findPanelByHeading("Next Suggestions"); if(!p) return; const r=await jget("/agent/next2"); log(p,"NEXT "+r.status+" "+(r.ok?"ok":"fail")); if(r.j){ log(p, pretty(r.j)); } }
  document.addEventListener("DOMContentLoaded",()=>{
    // expose helpers globally for other modules
    window.PA = window.PA || {}; Object.assign(window.PA,{doSummary,doPlan,doRecent,doNext});
  });
})();

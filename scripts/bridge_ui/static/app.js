const $ = s=>document.querySelector(s);
function cls(el,c){ el.classList.remove("dot-green","dot-amber","dot-red"); el.classList.add(c); }
let lastServices = {};
async function j(u,o){ try{ const r=await fetch(u,o||{}); return await r.json(); }catch{return null} }
function row(k,v){ const alive=!!v.alive; const pid=v.pid??"-"; const b=alive?`<span class="badge ok">alive</span>`:`<span class="badge down">down</span>`; return `<tr><td>${k}</td><td>${pid}</td><td>${b}</td></tr>`;}
function render(sv){ const rows=Object.entries(sv).map(([k,v])=>row(k,v)).join(""); $("#services").innerHTML = `<table><thead><tr><th>Service</th><th>PID</th><th>Status</th></tr></thead><tbody>${rows||"<tr><td colspan=3>no data</td></tr>"}</tbody></table>`;}
async function refresh(){
  const sup=await j("/api/supervisor"); const dot=$("#supDot");
  if(!sup||sup.healthy===false){ cls(dot,"dot-amber"); render(lastServices); } else { cls(dot,"dot-green"); lastServices=sup.services||{}; render(lastServices); }
  const tun=await j("/api/tunnel"); $("#tunnelHost").textContent=(tun&&tun.hostname)?tun.hostname:"—";
  const plan=await j("/api/plan"); const p=plan||{}; $("#planBlock").textContent=p.name?`${p.name} — phase ${p.phase||"?"} — ${p.status||"?"}`:"No plan loaded";
  const tail=await j("/api/log_tail?n=7000"); $("#logTail").textContent=(tail&&tail.text)?tail.text:"";
}
setInterval(refresh,1500); refresh();
$("#sendNowBtn").addEventListener("click", async()=>{ const r=await j("/api/tunnel/send_now",{method:"POST"}); if(!r||!r.ok) alert("Send failed: "+(r&&(r.err||r.rc))); });
$("#planRestartBtn").addEventListener("click", async()=>{ await j("/api/plan/restart",{method:"POST"}); });
const helpBtn=$("#helpBtn"), helpModal=$("#helpModal"), helpClose=$("#helpClose");
helpBtn.addEventListener("click",()=>helpModal.classList.remove("hidden"));
helpClose.addEventListener("click",()=>helpModal.classList.add("hidden"));
helpModal.addEventListener("click",(e)=>{ if(e.target===helpModal) helpModal.classList.add("hidden"); });

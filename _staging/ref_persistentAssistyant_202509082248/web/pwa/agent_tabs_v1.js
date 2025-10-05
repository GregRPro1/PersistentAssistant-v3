(function(){
  var Tabs=null; // will be inferred from headings
  function norm(s){return (s||"").replace(/\s+/g," ").trim().toLowerCase()}
  function Q(s,r){return (r||document).querySelector(s)}
  function QA(s,r){return Array.prototype.slice.call((r||document).querySelectorAll(s))}
  function findPanels(){
    var heads=QA("h1,h2,h3,h4,h5"); var out={};
    heads.forEach(function(h){ var txt=(h.textContent||"").trim(); if(!txt) return;
      var sec=h.closest("section,div")||h.parentElement; if(!sec) return;
      if(!out[txt]){ out[txt]=sec; sec.setAttribute("data-pa-panel",txt); }
    });
    return out;
  }
  var panels={}, tabs={}, wired=false;
  function ensure(){
    panels = findPanels();
    if(!Tabs){ Tabs = Object.keys(panels); }
    // discover declared tab buttons/links (require explicit data attr to avoid hijacking other buttons)
    QA("[data-pa-tab]").forEach(function(el){ var n=el.getAttribute("data-pa-tab"); if(n && !tabs[n]) tabs[n]=el; });
    // if none declared, inject fallback nav
    var haveAny = Object.keys(tabs).length>0;
    if(!haveAny){
      var nav=Q("#pa-fallback-nav");
      if(!nav){
        nav=document.createElement("div"); nav.id="pa-fallback-nav"; nav.style.cssText="position:sticky;top:0;z-index:10;padding:.5rem;background:#0f172a;color:#e2e8f0;display:flex;gap:.5rem;flex-wrap:wrap";
        Tabs.forEach(function(n){ var b=document.createElement("button"); b.textContent=n; b.setAttribute("data-pa-tab",n); b.style.cssText="padding:.25rem .5rem;border-radius:.5rem;border:1px solid #334155;background:#1e293b;color:#e2e8f0;cursor:pointer"; nav.appendChild(b); tabs[n]=b; });
        document.body.insertBefore(nav, document.body.firstChild);
      }
    }
  }
  function hideAll(){ Object.keys(panels).forEach(function(k){ var el=panels[k]; if(el) el.classList.add("pa-hide"); }); }
  function setActive(name){
    ensure(); hideAll();
    var shown=false;
    Object.keys(panels).forEach(function(k){ var el=panels[k]; if(el && k===name){ el.classList.remove("pa-hide"); shown=true; } });
    Object.keys(tabs).forEach(function(k){ var el=tabs[k]; if(!el) return; if(k===name){ el.classList.add("active"); } else { el.classList.remove("active"); } });
    try{ localStorage.setItem("pa.activeTab", name); }catch(e){}
    var h="#tab="+encodeURIComponent(name);
    if(location.hash!==h){ try{ history.replaceState(null,"",h); }catch(e){ location.hash=h; } }
    if(!shown){ var first=Tabs && Tabs[0]; if(first && panels[first]) panels[first].classList.remove("pa-hide"); }
  }
  function initial(){
    var name=null;
    if(location.hash && location.hash.indexOf("#tab=")===0){ name=decodeURIComponent(location.hash.substring(5)); }
    if(!name){ try{name=localStorage.getItem("pa.activeTab");}catch(e){} }
    if(!name){ name=(Object.keys(findPanels())[0]||"Summary"); }
    return name;
  }
  function boot(){ ensure(); if(!wired){
      document.addEventListener("click", function(ev){
        var el=ev.target; var root=el.closest("#pa-fallback-nav,[data-pa-tab]");
        if(root){ var n = root.getAttribute("data-pa-tab") || el.getAttribute("data-pa-tab") || (root.textContent||"").trim(); if(n){ ev.preventDefault(); setActive(n); } }
      }, true); wired=true; }
    setActive(initial());
  }
  document.addEventListener("DOMContentLoaded", function(){ boot(); setTimeout(boot,150); setTimeout(boot,800); });
  window.addEventListener("hashchange", function(){ var h=location.hash; if(h&&h.indexOf("#tab=")===0){ setActive(decodeURIComponent(h.substring(5))); } });
})();

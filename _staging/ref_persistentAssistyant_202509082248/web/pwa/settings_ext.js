/* settings_ext.js — robust UI ext v2 */
(function(){
  const TAG = "ext-ui-v2";
  const log = (...a)=>console.log(`[${TAG}]`, ...a);
  const err = (...a)=>console.error(`[${TAG}]`, ...a);

  const once = (fn)=>{ let done=false; return (...a)=>{ if (!done){ done=true; try{ fn(...a);}catch(e){err("init failed",e);} } } };

  const el = (tag, attrs={}, ...kids) => {
    const n = document.createElement(tag);
    Object.entries(attrs).forEach(([k,v])=>{
      if (k==="class") n.className=v;
      else if (k==="text") n.textContent=v;
      else n.setAttribute(k,v);
    });
    kids.forEach(k=>{ if (k) n.appendChild(typeof k==="string"?document.createTextNode(k):k); });
    return n;
  };

  async function jget(url) {
    const r = await fetch(url, {headers:{"Accept":"application/json"}});
    if (!r.ok) throw new Error(`${url} ${r.status}`);
    return r.json();
  }
  async function jpost(url, bodyObj) {
    const r = await fetch(url, {
      method:"POST",
      headers:{"Content-Type":"application/json","Accept":"application/json"},
      body: JSON.stringify(bodyObj||{})
    });
    let body; try{ body=await r.json(); }catch(_){}
    if (!r.ok) throw new Error(`${url} ${r.status} ${body?JSON.stringify(body):""}`);
    return body;
  }

  function findSettingsMount() {
    const explicit = document.querySelector("#extSettingsMount");
    if (explicit) { log("settings mount: #extSettingsMount"); return explicit; }

    const tok = document.getElementById("tok");
    if (tok && tok.closest(".panel")) {
      log("settings mount: closest(.panel) from #tok");
      return tok.closest(".panel");
    }

    const idGuess = document.getElementById("settingsPanel");
    if (idGuess) { log("settings mount: #settingsPanel"); return idGuess; }

    const dataPanel = document.querySelector('[data-panel="settings"]');
    if (dataPanel) { log('settings mount: [data-panel="settings"]'); return dataPanel; }

    const tabPanel = document.querySelector('#settings'); // generic fallback
    if (tabPanel) { log("settings mount: #settings"); return tabPanel; }

    err("settings mount not found");
    return null;
  }

  function findActionsMount() {
    const explicit = document.querySelector("#actionsMount");
    if (explicit) { log("actions mount: #actionsMount"); return explicit; }

    const idGuess = document.getElementById("actionsPanel");
    if (idGuess) { log("actions mount: #actionsPanel"); return idGuess; }

    const dataPanel = document.querySelector('[data-panel="actions"]');
    if (dataPanel) { log('actions mount: [data-panel="actions"]'); return dataPanel; }

    const header = Array.from(document.querySelectorAll("h2,h1,.panel h2,.panel h1"))
      .find(h => /Actions/i.test(h.textContent||""));
    if (header && header.closest(".panel")) { log("actions mount: nearest .panel to Actions header"); return header.closest(".panel"); }

    err("actions mount not found");
    return null;
  }

  function settingsBox(initialJson) {
    const wrap = el("div", {class:"card"});
    const title = el("div", {class:"panel-title", text:"Extended Settings (debug)"});
    const ta   = el("textarea", {style:"width:100%;height:8rem;white-space:pre; font-family:monospace;"});
    ta.value = JSON.stringify(initialJson||{}, null, 2);

    const save = el("button", {class:"btn"}, document.createTextNode("Save JSON"));
    save.addEventListener("click", async ()=>{
      try {
        const parsed = JSON.parse(ta.value || "{}");
        const res = await jpost("/agent/settings", parsed);
        log("settings saved", res);
        alert("Settings saved.");
      } catch(e) {
        err("save failed", e);
        alert("Save failed: "+ e);
      }
    });

    wrap.appendChild(title);
    wrap.appendChild(ta);
    wrap.appendChild(el("div", {style:"margin-top:.5rem"}, save));
    return wrap;
  }

  function actionsBox(cfg) {
    const wrap = el("div", {class:"card"});
    const title = el("div", {class:"panel-title", text:"Agent actions"});
    const out = el("pre", {style:"background:#111;padding:.5rem;border-radius:.5rem;overflow:auto;max-height:12rem;"}, "Ready.");
    const btn = el("button", {class:"btn"}, "Pilot next step (dry-run)");
    btn.addEventListener("click", async ()=>{
      try {
        const tests = (cfg && cfg.tests_default) || "tests";
        const plan  = (cfg && cfg.plan_file) || "";
        const iters = (cfg && cfg.auto_revise_default_iters) || 2;
        const cmd = [
          "python","-m","tools.py.agentic.auto_next",
          plan ? `--plan "${plan}"` : "",
          "--pilot",
          `--tests "${tests}"`,
          "--pytest-flags -q",
          `--iters ${iters}`
        ].filter(Boolean).join(" ");

        out.textContent = "Running:\n"+cmd+"\n\n";
        const res = await jpost("/agent/leb/run", {cmd});
        out.textContent += JSON.stringify(res, null, 2);
      } catch(e) {
        err("leb run failed", e);
        out.textContent += "\nERROR: " + e;
      }
    });

    wrap.appendChild(title);
    wrap.appendChild(btn);
    wrap.appendChild(out);
    return wrap;
  }

  const init = once(async ()=>{
    log("DOMContentLoaded");
    let cfg = {};
    try {
      cfg = await jget("/agent/settings");
      log("GET /agent/settings OK", cfg);
    } catch(e) {
      err("GET /agent/settings failed", e);
    }

    const sm = findSettingsMount();
    if (sm) {
      try {
        sm.appendChild(settingsBox(cfg));
      } catch(e) {
        err("mount settings box failed", e);
      }
    }

    const am = findActionsMount();
    if (am) {
      try {
        am.appendChild(actionsBox(cfg));
      } catch(e) {
        err("mount actions box failed", e);
      }
    }
  });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();

import json, os, datetime, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREVIEW = ROOT / "tools" / "phone_preview.py"
STATIC  = ROOT / "tools" / "phone_static"
CFG     = ROOT / "config" / "phone" / "phone.yaml"
TMP     = ROOT / "tmp"
APPROVE_DIR = TMP / "phone" / "approvals"
APPROVE_DIR.mkdir(parents=True, exist_ok=True)
STATIC.mkdir(parents=True, exist_ok=True)

summary = {"ok": True, "changes": [], "warnings": [], "errors": []}

def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""

def _write(p: Path, text: str):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    summary["changes"].append(f"wrote {p}")

def _json(obj): return json.dumps(obj, ensure_ascii=False, indent=2)

def _get_token():
    # phone.yaml: token: "...."
    if not CFG.exists():
        summary["warnings"].append(f"{CFG} missing; create config/phone/phone.yaml with token")
        return None
    import yaml
    try:
        d = yaml.safe_load(CFG.read_text(encoding="utf-8")) or {}
        t = d.get("token")
        if not t: summary["warnings"].append("phone.yaml has no token")
        return t
    except Exception as e:
        summary["warnings"].append(f"phone.yaml parse error: {e}")
        return None

# --- 1A) Patch phone_preview.py with POST /phone/approve and GET /phone/latest_pack
body = _read(PREVIEW)
if not body:
    summary["warnings"].append(f"{PREVIEW} not found; phone server must be started via your existing scripts")
# Insert serve+cors if missing (idempotent; also covers /phone/options if needed)
if "BEGIN PHONE PWA SERVE + CORS" not in body:
    block = """
# === BEGIN PHONE PWA SERVE + CORS ===
try:
    from flask import send_from_directory, request, jsonify
except Exception:
    send_from_directory = None
    request = None
    jsonify = None

try:
    @app.after_request
    def add_cors_headers(resp):
        try:
            origin = request.headers.get("Origin", "*") if request else "*"
            resp.headers["Access-Control-Allow-Origin"] = origin
            resp.headers["Access-Control-Allow-Headers"] = "Content-Type,X-Phone-Token"
            resp.headers["Vary"] = "Origin"
        except Exception:
            pass
        return resp
except Exception:
    pass

import os, json, datetime
PWA_DIR = os.path.join(os.path.dirname(__file__), "phone_static")
TMP_DIR = os.path.join(os.path.dirname(__file__), "..", "tmp")
APPROVE_DIR = os.path.normpath(os.path.join(TMP_DIR, "phone", "approvals"))

if send_from_directory:
    @app.route("/phone/app")
    def phone_app():
        return send_from_directory(PWA_DIR, "index.html")

    @app.route("/phone/static/<path:fname>")
    def phone_static(fname):
        return send_from_directory(PWA_DIR, fname)
# === END PHONE PWA SERVE + CORS ===
""".lstrip("\n")
    if body and not body.endswith("\n"): body += "\n"
    body += block
    summary["changes"].append("inserted PWA SERVE + CORS block")

# Ensure /phone/options route
if "BEGIN PHONE OPTIONS" not in body:
    block = """
# === BEGIN PHONE OPTIONS ===
if send_from_directory:
    @app.route("/phone/options")
    def phone_options():
        return send_from_directory(PWA_DIR, "options.json")
# === END PHONE OPTIONS ===
""".lstrip("\n")
    if body and not body.endswith("\n"): body += "\n"
    body += block
    summary["changes"].append("inserted /phone/options route")

# Add /phone/approve (token required) + /phone/latest_pack
if "BEGIN PHONE APPROVE" not in body:
    block = """
# === BEGIN PHONE APPROVE ===
def _latest_pack_path():
    import glob, os
    fb = os.path.normpath(os.path.join(TMP_DIR, "feedback"))
    if not os.path.isdir(fb): return None
    cands = []
    for pat in ("pack_*.zip","pack_apply_pack_*.zip"):
        cands.extend(glob.glob(os.path.join(fb, pat)))
    if not cands: return None
    cands.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return os.path.normpath(cands[0])

def _config_token():
    try:
        import yaml
        cfg = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "config", "phone", "phone.yaml"))
        with open(cfg, "r", encoding="utf-8") as f:
            d = yaml.safe_load(f) or {}
        return d.get("token")
    except Exception:
        return None

if jsonify:
    @app.route("/phone/approve", methods=["POST"])
    def phone_approve():
        tok = _config_token()
        hdr = request.headers.get("X-Phone-Token", "")
        if not tok or hdr != str(tok):
            return jsonify({"ok": False, "error": "unauthorized"}), 401
        try:
            data = request.get_json(silent=True) or {}
            choice = data.get("choice") or data.get("phrase")
            payload = {
                "choice": choice,
                "received_at": datetime.datetime.utcnow().isoformat()+"Z",
                "user_agent": request.headers.get("User-Agent",""),
                "remote_addr": request.remote_addr,
            }
            os.makedirs(APPROVE_DIR, exist_ok=True)
            with open(os.path.join(APPROVE_DIR, f"approval_{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"), "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            with open(os.path.join(APPROVE_DIR, "latest.json"), "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            return jsonify({"ok": True, "stored": True, "echo": payload})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/phone/latest_pack")
    def phone_latest_pack():
        p = _latest_pack_path()
        return jsonify({"ok": bool(p), "latest_pack": p})
# === END PHONE APPROVE ===
""".lstrip("\n")
    if body and not body.endswith("\n"): body += "\n"
    body += block
    summary["changes"].append("inserted /phone/approve and /phone/latest_pack")

if "inserted" in " ".join(summary["changes"]):
    _write(PREVIEW, body)

# --- 1B) Ensure static files: options + enhanced app.js with Send + Latest PACK
opts_path = STATIC / "options.json"
opts = {
    "version": "1.1",
    "options": [
        {"key": "1", "label": "Run next planned step",       "phrase": "APPROVE NEXT"},
        {"key": "2", "label": "Re-run last step",             "phrase": "APPROVE RETRY"},
        {"key": "3", "label": "Request diagnostics bundle",   "phrase": "REQUEST DIAGNOSTICS"},
        {"key": "4", "label": "Approve PWA enhancements",     "phrase": "APPROVE 7.4 PWA-ENHANCE"}
    ],
    "generated_at": datetime.datetime.utcnow().isoformat()+"Z"
}
_write(opts_path, _json(opts))

index_path = STATIC / "index.html"
if not index_path.exists():
    _write(index_path, """<!doctype html>
<html>
  <head><meta charset="utf-8"><title>PA Phone</title>
    <meta name="viewport" content="width=device-width, initial-scale=1"/>
    <style>body{font-family:system-ui;margin:16px} .err{color:#b00} .row{margin:8px 0}</style>
  </head>
  <body>
    <h1>Persistent Assistant — Phone</h1>
    <div class="row">
      <label>Token: <input id="tok" placeholder="paste once; stored locally"/></label>
      <button id="saveTok">Save</button>
    </div>
    <div class="row"><strong>Latest PACK:</strong> <span id="lp">…</span> <button id="copyLP">Copy</button></div>
    <div class="row"><h2>Actions</h2><ol id="options"><li>Loading…</li></ol></div>
    <pre id="out"></pre>
    <script src="/phone/static/app.js"></script>
  </body>
</html>""")

appjs = STATIC / "app.js"
txt = _read(appjs)
need_latest = "phone/latest_pack" not in txt
need_approve = "phone/approve" not in txt
if need_latest or need_approve or not txt:
    _write(appjs, """(function(){
  const $ = sel => document.querySelector(sel);
  const out = $('#out');
  const tokIn = $('#tok');
  const save = $('#saveTok');
  const lp = $('#lp');
  const copyLP = $('#copyLP');

  // token persistence
  const KEY='pa_phone_token';
  tokIn.value = localStorage.getItem(KEY)||'';
  save.onclick = ()=>{ localStorage.setItem(KEY, tokIn.value||''); };

  function log(s){ out.textContent = (out.textContent? out.textContent + "\\n":"") + s; }

  function renderOptions(){
    fetch('/phone/options').then(r=>r.json()).then(o=>{
      const list = $('#options'); list.innerHTML='';
      (o.options||[]).forEach(it=>{
        const li = document.createElement('li');
        const btn = document.createElement('button');
        btn.textContent = `${it.key}) ${it.label}`;
        btn.onclick = ()=>{
          const tok = localStorage.getItem(KEY)||'';
          fetch('/phone/approve',{method:'POST', headers:{
            'Content-Type':'application/json',
            'X-Phone-Token': tok
          }, body: JSON.stringify({choice: it.key, phrase: it.phrase})})
          .then(r=>r.json()).then(j=>{ log(JSON.stringify(j)); })
          .catch(e=>log('ERR '+e.message));
        };
        li.appendChild(btn);
        const span = document.createElement('span');
        span.style.marginLeft='8px';
        span.textContent = ` say: ${it.phrase}`;
        li.appendChild(span);
        list.appendChild(li);
      });
    }).catch(e=>log('Options error: '+e.message));
  }

  function pollLatestPack(){
    fetch('/phone/latest_pack').then(r=>r.json()).then(j=>{
      lp.textContent = j.latest_pack || '—';
    }).catch(e=>{ lp.textContent = '—'; });
  }
  copyLP.onclick = ()=>{
    navigator.clipboard.writeText(lp.textContent||'').catch(()=>{});
  };

  renderOptions();
  pollLatestPack();
  setInterval(pollLatestPack, 5000);
})();""")

print(_json(summary))

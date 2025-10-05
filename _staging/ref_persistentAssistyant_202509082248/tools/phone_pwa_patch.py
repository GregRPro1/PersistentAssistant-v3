import json, os, io, sys, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
preview = ROOT / "tools" / "phone_preview.py"
static  = ROOT / "tools" / "phone_static"
static.mkdir(parents=True, exist_ok=True)

summary = {
    "ok": True,
    "changes": [],
    "warnings": [],
    "errors": []
}

def _load_text(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except FileNotFoundError:
        summary["warnings"].append(f"{p} not found; creating stub.")
        return ""

def _save_text(p: Path, text: str):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    summary["changes"].append(f"wrote {p}")

# 1) Ensure preview has PWA routes + CORS
body = _load_text(preview)
need_pwa = "BEGIN PHONE PWA SERVE + CORS" not in body
need_opt = "BEGIN PHONE OPTIONS" not in body

if need_pwa:
    block = """
# === BEGIN PHONE PWA SERVE + CORS ===
try:
    from flask import send_from_directory, request
except Exception:
    send_from_directory = None
    request = None

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

import os
PWA_DIR = os.path.join(os.path.dirname(__file__), "phone_static")

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

if need_opt:
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

if need_pwa or need_opt:
    _save_text(preview, body)

# 2) Ensure static assets
options_path = static / "options.json"
index_path   = static / "index.html"
appjs_path   = static / "app.js"

# options.json (approval schema)
options = {
    "version": "1.0",
    "options": [
        {"key": "1", "label": "Run next planned step",           "phrase": "APPROVE NEXT"},
        {"key": "2", "label": "Re-run last step",                 "phrase": "APPROVE RETRY"},
        {"key": "3", "label": "Request detailed diagnostics",     "phrase": "REQUEST DIAGNOSTICS"},
        {"key": "4", "label": "Approve PWA enhancements",         "phrase": "APPROVE 7.4 PWA-ENHANCE"}
    ],
    "generated_at": datetime.datetime.utcnow().isoformat()+"Z"
}
_save_text(options_path, json.dumps(options, ensure_ascii=False, indent=2))

# index.html: minimal shell if missing
if not index_path.exists():
    _save_text(index_path, """<!doctype html>
<html>
  <head><meta charset="utf-8"><title>PA Phone</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <style>body{font-family:system-ui;margin:16px} .err{color:#b00}</style>
  </head>
  <body>
    <h1>Persistent Assistant — Phone</h1>
    <div id="digest"></div>
    <h2>Actions</h2>
    <ol id="options"><li>Loading options…</li></ol>
    <script src="/phone/static/app.js"></script>
  </body>
</html>""")

# app.js: fetch + render options if needed; otherwise ensure it calls /phone/options
need_write_js = True
if appjs_path.exists():
    txt = appjs_path.read_text(encoding="utf-8")
    if 'fetch("/phone/options")' in txt or "fetch('/phone/options')" in txt:
        need_write_js = False

if need_write_js:
    _save_text(appjs_path, """(function(){
  function renderOptions(){
    const el = document.querySelector('#options'); el.innerHTML='';
    fetch('/phone/options').then(r=>{
      if(!r.ok) throw new Error('HTTP '+r.status);
      return r.json();
    }).then(o=>{
      (o.options||[]).forEach(it=>{
        const li = document.createElement('li');
        li.textContent = `${it.key}) ${it.label} — say: ${it.phrase}`;
        el.appendChild(li);
      });
    }).catch(e=>{
      const li = document.createElement('li');
      li.textContent = 'Options unavailable: '+e.message;
      li.className='err';
      el.appendChild(li);
    });
  }
  renderOptions();
})();""")

print(json.dumps(summary, ensure_ascii=False, indent=2))

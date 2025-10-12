from __future__ import annotations
import os
from pathlib import Path
from flask import Flask, request, redirect, url_for, render_template_string
try:
    import yaml
except ImportError:
    yaml = None

APP_HOST = os.environ.get("WATCHDOG_HOST", "127.0.0.1")
APP_PORT = int(os.environ.get("WATCHDOG_PORT", "8787"))
SETTINGS_PATH = Path(r"C:\_Repos\PersistentAssistant\config\pal_settings.yaml")

app = Flask(__name__)

def _load_yaml(path: Path) -> dict:
    if not path.exists() or yaml is None:
        return {}
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}

def _dump_yaml(path: Path, data: dict) -> None:
    if yaml is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")

def _norm_win_path(p: str) -> str:
    if p is None:
        return ""
    p = str(p).strip().strip('"').strip("'")
    return str(Path(p)).replace("/", "\\")

def save_settings_number_and_tracker(number: str, tracker: str) -> None:
    cfg = _load_yaml(SETTINGS_PATH)
    cfg.setdefault("whatsapp", {})
    cfg.setdefault("paths", {})
    cfg["whatsapp"]["number"] = (number or "").replace(" ", "")
    cfg["paths"]["tracker_script"] = _norm_win_path(tracker or "")
    _dump_yaml(SETTINGS_PATH, cfg)

@app.get("/healthz")
def healthz():
    return "ok", 200

@app.get("/__debug")
def dbg():
    return {"env": {"PAL_MASTER": os.environ.get("PAL_MASTER"), "PAL_CHILD": os.environ.get("PAL_CHILD")}}, 200

INDEX_HTML = """
<h2>Watchdog UI (Basic)</h2>
<ul>
  <li><a href="{{ url_for('settings') }}">Settings</a></li>
  <li><a href="{{ url_for('context_tools') }}">Context Tools</a></li>
  <li><a href="{{ url_for('healthz') }}">/healthz</a></li>
  <li><a href="{{ url_for('dbg') }}">/__debug</a></li>
</ul>
<p>Listening on http://{{host}}:{{port}}</p>
"""

@app.get("/")
def index():
    return render_template_string(INDEX_HTML, host=APP_HOST, port=APP_PORT)

SETTINGS_HTML = """
<h3>Settings</h3>
<form method="post">
  <label>WhatsApp Number</label><br/>
  <input name="whatsapp_number" value="{{num}}"/><br/><br/>
  <label>Tracker Script Path</label><br/>
  <input name="tracker_script" size="80" value="{{trk}}"/><br/><br/>
  <button type="submit">Save</button>
</form>
<p>Current file: {{settings_path}}</p>
<p><a href="{{ url_for('index') }}">Back</a></p>
"""

@app.route("/settings", methods=["GET", "POST"])
def settings():
    if request.method == "POST":
        number = request.form.get("whatsapp_number","")
        tracker = request.form.get("tracker_script","")
        save_settings_number_and_tracker(number, tracker)
        return redirect(url_for("settings"))
    cfg = _load_yaml(SETTINGS_PATH)
    num = (cfg.get("whatsapp",{}) or {}).get("number","")
    trk = (cfg.get("paths",{}) or {}).get("tracker_script","")
    return render_template_string(SETTINGS_HTML, num=num, trk=trk, settings_path=str(SETTINGS_PATH))

CONTEXT_HTML = """
<h3>Context Tools</h3>
<form action="{{ url_for('context_action') }}" method="post">
  <label>Master ID</label><input name="master" value="{{master}}"/><br/>
  <label>Child ID</label><input name="child" value="{{child}}"/><br/><br/>
  <button name="op" value="load">Load Master</button>
  <button name="op" value="capture">Capture Child</button>
  <button name="op" value="close">Close Child</button>
</form>
<pre>{{out}}</pre>
<p><a href="{{ url_for('index') }}">Back</a></p>
"""

@app.get("/context")
def context_tools():
    return render_template_string(
        CONTEXT_HTML,
        master=os.environ.get("PAL_MASTER","PAL20251012"),
        child=os.environ.get("PAL_CHILD","PAL20251012B"),
        out=""
    )

@app.post("/context")
def context_action():
    import subprocess
    master = request.form.get("master","").strip()
    child = request.form.get("child","").strip()
    op = request.form.get("op")
    repo_root = Path(__file__).resolve().parents[2]
    script_dir = repo_root / "tools" / "context"
    cmd = ["pwsh","-NoProfile"]
    if op == "load":
        cmd += [str(script_dir / "context_loader.ps1"), "-MasterId", master]
    elif op == "capture":
        cmd += [str(script_dir / "context_capture.ps1"), "-MasterId", master, "-ChildId", child]
    elif op == "close":
        cmd += [str(script_dir / "context_close.ps1"), "-MasterId", master, "-ChildId", child]
    else:
        return "Unknown op", 400
    try:
        cp = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        out = (cp.stdout or "") + (cp.stderr or "")
    except Exception as e:
        out = f"ERR: {e}"
    return render_template_string(
        CONTEXT_HTML,
        master=master, child=child, out=out
    )

if __name__ == "__main__":
    print(f"Watchdog UI running → http://{APP_HOST}:{APP_PORT}")
    app.run(host=APP_HOST, port=APP_PORT, debug=False, threaded=False)

# === PAL_CTX_DYNAMIC_IMPORT START ===
try:
    import importlib.util, pathlib, sys
    _p = pathlib.Path(__file__).with_name("_ctx_panel.py")
    if _p.exists():
        _spec = importlib.util.spec_from_file_location("pal_ctx_panel", str(_p))
        _mod  = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_mod)  # type: ignore
        if 'app' in globals():
            _mod.register_ctx_panel(app)
except Exception:
    pass
# === PAL_CTX_DYNAMIC_IMPORT END ===

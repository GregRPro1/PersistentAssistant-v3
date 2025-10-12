#!/usr/bin/env python3
import os, sys, time, subprocess, datetime, shutil, re, threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs
from pathlib import Path
import urllib.request

# ---------- Config ----------
REPO = Path(r"C:\_Repos\PersistentAssistant")
LOG_DIR = REPO / "logs"
WD_LOG = LOG_DIR / "watchdog"
CF_LOG_DIR = LOG_DIR / "cloudflared"
PLAN = REPO / "pal_project_plan.yaml"
POLL_SECONDS = 5
AUTORESTART_ENABLED = False
AUTORESTART_INTERVAL_SEC = 60
AUTORESTART_MAX = 5  # -1 for infinite

# ---------- Setup ----------
for d in (WD_LOG, CF_LOG_DIR):
    d.mkdir(parents=True, exist_ok=True)

def utcnow():
    return datetime.datetime.now(datetime.timezone.utc)

def ts():
    return utcnow().strftime("%Y%m%d_%H%M%S")

# ---------- Services ----------
SERVICES = {
    "pal-dev-server": {
        "cmd": ["python", str(REPO / "current" / "server_wrapper.py")],
        "cwd": str(REPO),
        "ports": [8787],
        "health": "http://127.0.0.1:8787",
        "logdir": WD_LOG,
    },
    "quick-tunnel": {
        "cmd": ["cloudflared", "tunnel", "--url", "http://127.0.0.1:8787", "--loglevel", "debug"],
        "cwd": str(REPO),
        "ports": [],
        "health": "",
        "logdir": CF_LOG_DIR,
    }
}

_HANDLES = {k: None for k in SERVICES}
_LOGFILES = {k: None for k in SERVICES}
_LAST_OK = {k: None for k in SERVICES}
_LAST_CHECK = {k: None for k in SERVICES}
_RESTARTS = {k: 0 for k in SERVICES}
_TRYCLOUDFLARE_URL = None
_URL_LAST_SEEN = None
_MONITOR_STOP = False

def log_path_for(name):
    return SERVICES[name]["logdir"] / f"{name}_{ts()}.log"

def _child_env():
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    return env

def start_service(name):
    if _HANDLES[name] and _HANDLES[name].poll() is None:
        return f"{name} already running (pid {_HANDLES[name].pid})"
    svc = SERVICES[name]
    logfile = log_path_for(name)
    f = open(logfile, "a", buffering=1, encoding="utf-8", errors="replace")
    cmd = " ".join(svc["cmd"]) if os.name == "nt" else svc["cmd"]
    p = subprocess.Popen(cmd, cwd=svc["cwd"], stdout=f, stderr=f, stdin=subprocess.DEVNULL,
                         shell=(os.name=="nt"), env=_child_env())
    _HANDLES[name] = p
    _LOGFILES[name] = logfile
    _RESTARTS[name] = 0
    return f"started {name} pid={p.pid} log={logfile.name}"

def stop_service(name):
    p = _HANDLES.get(name)
    if not p or p.poll() is not None:
        _HANDLES[name] = None
        return f"{name} not running"
    try:
        p.terminate()
        for _ in range(25):
            if p.poll() is not None: break
            time.sleep(0.2)
        if p.poll() is None: p.kill()
    except Exception as e:
        return f"error stopping {name}: {e}"
    _HANDLES[name] = None
    return f"stopped {name}"

def restart_service(name):
    stop_service(name)
    time.sleep(0.2)
    return start_service(name)

def _head_ok(url, timeout=2.5):
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status < 400
    except Exception:
        return False

def service_status(name):
    p = _HANDLES.get(name)
    running = bool(p and p.poll() is None)
    pid = p.pid if running else None
    healthy = False
    url = SERVICES[name].get("health") or ""
    if url and running:
        healthy = _head_ok(url)
    elif running:
        healthy = True
    if healthy:
        _LAST_OK[name] = utcnow()
    _LAST_CHECK[name] = utcnow()
    return running, pid, healthy

# ---------- URL extraction ----------
URL_PAT = re.compile(r"https://[A-Za-z0-9\-\.]+\.trycloudflare\.com")
def update_trycloudflare_url():
    global _TRYCLOUDFLARE_URL, _URL_LAST_SEEN
    logs = sorted(CF_LOG_DIR.glob("quick-tunnel_*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not logs: return
    path = logs[0]
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                m = URL_PAT.search(line)
                if m:
                    _TRYCLOUDFLARE_URL = m.group(0)
                    _URL_LAST_SEEN = utcnow()
    except Exception:
        pass

# ---------- Monitor ----------
def monitor_loop():
    while not _MONITOR_STOP:
        for name in SERVICES:
            running, pid, ok = service_status(name)
            if AUTORESTART_ENABLED and not ok:
                last = _LAST_CHECK.get(name)
                if not last or (utcnow()-last).total_seconds() >= AUTORESTART_INTERVAL_SEC:
                    if AUTORESTART_MAX < 0 or _RESTARTS[name] < AUTORESTART_MAX:
                        restart_service(name); _RESTARTS[name] += 1
        update_trycloudflare_url()
        time.sleep(POLL_SECONDS)

# ---------- Helpers ----------
def fmt_age(dt):
    if not dt: return "never"
    secs = int((utcnow()-dt).total_seconds())
    if secs < 60: return f"{secs}s ago"
    mins = secs//60
    if mins < 60: return f"{mins}m ago"
    return f"{mins//60}h ago"

def git_commit_logs(msg):
    try:
        subprocess.run(["git","-C",str(REPO),"add","logs"], check=False)
        subprocess.run(["git","-C",str(REPO),"commit","-m",msg], check=False)
        return True
    except Exception:
        return False

# ---------- UI ----------
CSS = """
:root{{--bg:#0b0d10;--fg:#e6e8eb;--muted:#9aa3ad;--card:#12161a;--accent:#4ea1ff;--good:#46d369;--bad:#ff6b6b}}
*{{box-sizing:border-box}} body{{font-family:Segoe UI,Arial,Helvetica,sans-serif;background:var(--bg);color:var(--fg);margin:0;padding:24px}}
h2{{margin:0 0 8px 0}} p.small{{color:var(--muted);margin:0 0 16px 0}}
.card{{background:var(--card);border:1px solid #1f252b;border-radius:12px;padding:14px 16px;margin:10px 0}}
button{{border:1px solid #2a3138;background:#171c21;color:var(--fg);padding:8px 12px;border-radius:8px;margin-right:8px;cursor:pointer}}
a{{color:var(--accent);text-decoration:none}} a:hover{{text-decoration:underline}}
.tag{{display:inline-block;padding:2px 8px;border-radius:999px;font-size:12px;margin-left:8px}}
.ok{{background:#0f2a19;color:var(--good);border:1px solid #204d33}} .bad{{background:#2a1717;color:var(--bad);border:1px solid #4d2020}}
pre{{background:#0e1116;border:1px solid #1f252b;border-radius:8px;padding:10px;max-height:360px;overflow:auto}}
hr{{border:0;border-top:1px solid #20262d;margin:18px 0}}
small.m{{color:var(--muted)}}
"""

def main_page():
    blocks = []
    for name in SERVICES:
        running, pid, ok = service_status(name)
        oktxt = "OK" if (running and ok) else "ISSUE"
        okcls = "ok" if (running and ok) else "bad"
        hb = fmt_age(_LAST_OK.get(name))
        blocks.append(f"""
        <div class="card">
          <b>{name}</b>
          <span class="tag {okcls}">{oktxt}</span>
          <div style="margin-top:8px;color:var(--muted)">
            pid:{pid} • running:{running} • health:{ok} • last ok:{hb} • restarts:{_RESTARTS[name]}
          </div>
          <div style="margin-top:10px">
            <form method="POST" action="/control" style="display:inline">
              <input type="hidden" name="service" value="{name}">
              <button name="action" value="start">Start</button>
              <button name="action" value="stop">Stop</button>
              <button name="action" value="restart">Restart</button>
            </form>
            <a href="/download?service={name}">Download latest log</a>
          </div>
        </div>
        """)
    url_block = f"""
    <div class="card"><b>Quick Tunnel URL</b><br>
      <div style="margin-top:6px">{_TRYCLOUDFLARE_URL or '<i>(not yet detected)</i>'}</div>
      <div style="margin-top:6px"><small class="m">last seen: {fmt_age(_URL_LAST_SEEN)}</small></div>
    </div>"""
    controls = f"""
    <div class="card">
      <b>Global controls</b><br>
      <form method="POST" action="/init" style="display:inline"><button name="action" value="initall">Initialize All</button></form>
      <form method="POST" action="/autorestart" style="display:inline;margin-left:10px"><button>{"Disable" if AUTORESTART_ENABLED else "Enable"} Autorestart</button></form>
      <form method="GET" action="/tracker" target="_blank" style="display:inline;margin-left:10px"><button>Open Tracker</button></form>
      <form method="POST" action="/commitlogs" style="display:inline;margin-left:10px"><button>Commit Logs</button></form>
      <div style="margin-top:6px"><small class="m">Autorestart: {AUTORESTART_ENABLED}, interval={AUTORESTART_INTERVAL_SEC}s, max={AUTORESTART_MAX}</small></div>
    </div>
    """
    logtail = """
    <h3>Log tail</h3>
    <form method="POST" action="/tail">
      <select name="service"><option>pal-dev-server</option><option>quick-tunnel</option></select>
      <button type="submit">Tail log</button>
    </form>"""
    html = f"""<html><head><meta charset='utf-8'><title>PAL Watchdog</title><style>{CSS}</style></head>
    <body><h2>PAL Watchdog</h2><p class="small">Controller, heartbeat, logs, URL extraction, tracker link (localhost only).</p>
    {''.join(blocks)}{url_block}{controls}{logtail}</body></html>"""
    return html

def render_plan():
    if not PLAN.exists():
        return "<i>No pal_project_plan.yaml found.</i>"
    lines = PLAN.read_text(encoding="utf-8", errors="replace").splitlines()
    html = ["<table style='width:100%;border-collapse:collapse'>"]
    html.append("<tr><th style='text-align:left;border-bottom:1px solid #333'>Phase</th><th style='text-align:left;border-bottom:1px solid #333'>Task</th><th style='text-align:left;border-bottom:1px solid #333'>Status</th><th style='text-align:left;border-bottom:1px solid #333'>Desc</th></tr>")
    phase = None; phase_status = ""
    for i,l in enumerate(lines):
        m = re.match(r'\s*-\s*id:\s*([A-Za-z0-9\.]+)', l)
        if m and '.' not in m.group(1):
            phase = m.group(1); phase_status = ""
            continue
        if phase and 'status:' in l and not phase_status:
            phase_status = l.split(':',1)[1].strip()
            continue
        tm = re.match(r'\s*-\s*id:\s*([A-Za-z0-9\.]+)', l)
        if tm and '.' in tm.group(1):
            task = tm.group(1); desc=""; status=""
            for j in range(i+1, min(i+8,len(lines))):
                if re.match(r'\s*-\s*id:', lines[j]): break
                if 'desc:' in lines[j]: desc = lines[j].split(':',1)[1].strip()
                if 'status:' in lines[j]: status = lines[j].split(':',1)[1].strip()
            html.append(f"<tr><td style='vertical-align:top'>{phase} <span style='color:#9aa3ad'>[{phase_status}]</span></td><td>{task}</td><td>{status}</td><td>{desc}</td></tr>")
    html.append("</table>")
    return "\n".join(html)

def tracker_page():
    return f"""<html><head><meta charset='utf-8'><title>PAL Tracker</title>
    <meta http-equiv="refresh" content="5"><style>{CSS}</style></head>
    <body><h2>PAL Tracker</h2><p class="small">Auto-refresh every 5s. Source: pal_project_plan.yaml</p>
    <div class="card">{render_plan()}</div>
    <div class="card"><b>Quick Tunnel URL</b><br>{_TRYCLOUDFLARE_URL or '<i>(not yet detected)</i>'}</div>
    </body></html>"""

class Handler(BaseHTTPRequestHandler):
    def _send(self, html, code=200, ctype="text/html; charset=utf-8"):
        self.send_response(code); self.send_header("Content-type", ctype); self.end_headers()
        self.wfile.write(html.encode("utf-8") if isinstance(html,str) else html)

    def do_GET(self):
        if self.path.startswith("/download"):
            q = parse_qs(self.path.split("?",1)[1]) if "?" in self.path else {}
            svc = q.get("service", ["pal-dev-server"])[0]
            lf = _LOGFILES.get(svc)
            if lf and Path(lf).exists():
                with open(lf, "rb") as f: data = f.read()
                self._send(data, 200, "text/plain; charset=utf-8"); return
            self._send("<pre>No logfile</pre>",404); return
        if self.path.startswith("/tracker"):
            self._send(tracker_page()); return
        self._send(main_page())

    def do_POST(self):
        length = int(self.headers.get("content-length",0)); body = self.rfile.read(length).decode("utf-8"); params = parse_qs(body)
        if self.path == "/control":
            svc = params.get("service", [""])[0]; action = params.get("action", [""])[0]
            if action == "start": start_service(svc)
            elif action == "stop": stop_service(svc)
            elif action == "restart": restart_service(svc)
            self.send_response(303); self.send_header("Location","/"); self.end_headers(); return
        if self.path == "/tail":
            svc = params.get("service", ["pal-dev-server"])[0]
            lf = _LOGFILES.get(svc)
            if not lf or not Path(lf).exists(): self._send(f"<pre>No logfile for {svc}</pre>",404); return
            with open(lf, "r", encoding="utf-8", errors="replace") as f: data = f.read().splitlines()[-250:]
            self._send("<html><body><pre>\n"+ "\n".join(data) + "\n</pre><p><a href='/'>Back</a></p></body></html>"); return
        if self.path == "/init":
            start_service("pal-dev-server")
            for _ in range(30):
                running, _, ok = service_status("pal-dev-server")
                if ok: break
                time.sleep(1)
            start_service("quick-tunnel")
            for _ in range(30):
                update_trycloudflare_url()
                if _TRYCLOUDFLARE_URL: break
                time.sleep(1)
            self.send_response(303); self.send_header("Location","/"); self.end_headers(); return
        if self.path == "/autorestart":
            global AUTORESTART_ENABLED
            AUTORESTART_ENABLED = not AUTORESTART_ENABLED
            self.send_response(303); self.send_header("Location","/"); self.end_headers(); return
        if self.path == "/commitlogs":
            ok = git_commit_logs("PAL: commit logs via watchdog UI")
            self._send(f"<html><body><pre>commit {'ok' if ok else 'failed'}</pre><a href='/'>Back</a></body></html>"); return
        if self.path == "/plan":
            # POST only updates plan via separate mark_task.py already present in repo.
            task = params.get("task", [""])[0]; status = params.get("status", ["NotStarted"])[0]
            if task:
                updater = REPO / "scripts" / "plan" / "mark_task.py"
                if updater.exists():
                    py = sys.executable or "python"
                    subprocess.run([py, str(updater), task, status], cwd=str(REPO), check=False)
            self.send_response(303); self.send_header("Location","/"); self.end_headers(); return

def run_ui(host="127.0.0.1", port=9001):
    t = threading.Thread(target=monitor_loop, daemon=True); t.start()
    httpd = HTTPServer((host, port), Handler)
    print(f"Watchdog UI listening at http://{host}:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        global _MONITOR_STOP; _MONITOR_STOP = True
        print("Stopping UI")

if __name__ == "__main__":
    run_ui()

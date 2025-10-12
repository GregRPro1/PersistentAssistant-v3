#!/usr/bin/env python3
import os, sys, time, subprocess, datetime, shutil
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs
from pathlib import Path
import urllib.request

REPO = Path(r"C:\_Repos\PersistentAssistant")
LOG_DIR = REPO / "logs"
WD_LOG = LOG_DIR / "watchdog"
CF_LOG_DIR = LOG_DIR / "cloudflared"
WD_LOG.mkdir(parents=True, exist_ok=True)
CF_LOG_DIR.mkdir(parents=True, exist_ok=True)

SERVICES = {
    "pal-dev-server": {
        "cmd": ["python", str(REPO / "current" / "server_wrapper.py")],
        "cwd": str(REPO),
        "ports": [8787],
        "health": "http://127.0.0.1:8787"
    },
    "quick-tunnel": {
        "cmd": ["cloudflared", "tunnel", "--url", "http://127.0.0.1:8787", "--loglevel", "debug"],
        "cwd": str(REPO),
        "ports": [],
        "health": ""
    }
}

_HANDLES = {}
_LOGFILES = {}

def ts(): return datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
def log_path_for(name): return (CF_LOG_DIR if name=="quick-tunnel" else WD_LOG) / f"{name}_{ts()}.log"

TEMPLATE = """<html><head><meta charset="utf-8"><title>PAL Watchdog</title>
<style>
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
</style></head><body>
<h2>PAL Watchdog</h2>
<p class="small">Controls and live logs (localhost only).</p>
{services}
<hr/>
<h3>Log tail</h3>
<form method="POST" action="/tail">
<select name="service">{options}</select>
<button type="submit">Tail log</button>
</form>
{tail}
</body></html>"""

SERVICE_BLOCK = """
<div class="card">
<b>{name}</b>
<span class="tag {okcls}">{oktxt}</span>
<div style="margin-top:8px;color:var(--muted)">pid:{pid} • running:{running} • health:{health}</div>
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
"""

def start_service(name):
    if name in _HANDLES and _HANDLES[name] and _HANDLES[name].poll() is None:
        return f"{name} already running (pid {_HANDLES[name].pid})"
    svc = SERVICES[name]
    logfile = log_path_for(name)
    f = open(logfile, "a", buffering=1, encoding="utf-8", errors="replace")
    cmd = " ".join(svc["cmd"]) if os.name=="nt" else svc["cmd"]
    # Force UTF-8 for child process stdout/stderr to avoid banner encode errors
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.Popen(cmd, cwd=svc["cwd"], stdout=f, stderr=f, stdin=subprocess.DEVNULL,
                            shell=(os.name=="nt"), env=env)
    _HANDLES[name] = proc; _LOGFILES[name] = logfile
    return f"started {name} pid={proc.pid} log={logfile.name}"

def stop_service(name):
    proc = _HANDLES.get(name)
    if not proc or proc.poll() is not None: _HANDLES[name] = None; return f"{name} not running"
    try:
        proc.terminate()
        for _ in range(25):
            if proc.poll() is not None: break
            time.sleep(0.2)
        if proc.poll() is None: proc.kill()
    except Exception as e:
        return f"error stopping {name}: {e}"
    _HANDLES[name] = None; return f"stopped {name}"

def restart_service(name): stop_service(name); time.sleep(0.2); return start_service(name)

def service_status(name):
    proc = _HANDLES.get(name); running = proc and proc.poll() is None; pid = proc.pid if running else None
    url = SERVICES[name].get("health") or ""; health = running if not url else False
    if url and running:
        try:
            req = urllib.request.Request(url, method="HEAD")
            with urllib.request.urlopen(req, timeout=1.5) as r: health = r.status < 400
        except Exception: health = False
    return {"running": bool(running), "pid": pid, "health": bool(health)}

class Handler(BaseHTTPRequestHandler):
    def _send(self, html, code=200):
        self.send_response(code); self.send_header("Content-type","text/html; charset=utf-8"); self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def do_GET(self):
        from pathlib import Path
        if self.path.startswith("/download"):
            q = parse_qs(self.path.split("?",1)[1]) if "?" in self.path else {}
            svc = q.get("service", ["pal-dev-server"])[0]
            lf = _LOGFILES.get(svc)
            if lf and Path(lf).exists():
                self.send_response(200); self.send_header("Content-Type","text/plain; charset=utf-8"); self.end_headers()
                with open(lf, "rb") as f: shutil.copyfileobj(f, self.wfile); return
            self._send(f"<pre>No logfile for {svc}</pre>", 404); return
        blocks, options, tail = [], [], ""
        for name in SERVICES.keys():
            st = service_status(name)
            oktxt = "OK" if (st["running"] and st["health"]) else "ISSUE"
            okcls = "ok" if (st["running"] and st["health"]) else "bad"
            blocks.append(SERVICE_BLOCK.format(name=name, pid=st["pid"], running=st["running"], health=st["health"], oktxt=oktxt, okcls=okcls))
            options.append(f"<option value='{name}'>{name}</option>")
        content = TEMPLATE.format(services="".join(blocks), options="".join(options), tail=tail)
        self._send(content)

    def do_POST(self):
        length = int(self.headers.get("content-length",0)); body = self.rfile.read(length).decode("utf-8"); params = parse_qs(body)
        if self.path == "/control":
            svc = params.get("service", [""])[0]; action = params.get("action", [""])[0]
            if action == "start": start_service(svc)
            elif action == "stop": stop_service(svc)
            elif action == "restart": restart_service(svc)
            self.send_response(303); self.send_header("Location","/"); self.end_headers(); return
        if self.path == "/tail":
            svc = params.get("service", ["pal-dev-server"])[0]; lf = _LOGFILES.get(svc)
            from pathlib import Path
            if not lf or not Path(lf).exists(): self._send(f"<pre>No logfile for {svc}</pre>",404); return
            try:
                with open(lf, "r", encoding="utf-8", errors="replace") as f: data = f.read().splitlines()[-250:]
                self._send("<html><body><pre>\n"+ "\n".join(data) + "\n</pre><p><a href='/'>Back</a></p></body></html>")
            except Exception as e:
                self._send(f"<pre>Error reading log: {e}</pre>",500)

def run_ui(host="127.0.0.1", port=9001):
    httpd = HTTPServer((host, port), Handler)
    print(f"Watchdog UI listening at http://{host}:{port}")
    try: httpd.serve_forever()
    except KeyboardInterrupt: print("Stopping UI")

if __name__ == "__main__":
    run_ui()

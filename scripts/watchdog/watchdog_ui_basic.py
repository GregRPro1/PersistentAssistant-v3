#!/usr/bin/env python3
import os, sys, re, json, time, subprocess, threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse
from pathlib import Path

REPO = Path(r"C:\_Repos\PersistentAssistant")
PORT = 9001
DEV_PORT = 8787
TRACKER_PORT = 9002
LOGS = REPO/"logs"; LOGS.mkdir(parents=True, exist_ok=True)
DEV_LOGS = LOGS/"dev_server"; DEV_LOGS.mkdir(parents=True, exist_ok=True)
TRK_LOGS = LOGS/"tracker"; TRK_LOGS.mkdir(parents=True, exist_ok=True)
CF_LOGS = LOGS/"cloudflared"; CF_LOGS.mkdir(parents=True, exist_ok=True)
STATIC = REPO/"scripts"/"watchdog"/"static"
URL_PAT = re.compile(r"https://[A-Za-z0-9\-\.]+\.trycloudflare\.com")
URL_FILE = CF_LOGS/"basic_quicktunnel_url.txt"

def _env_utf8():
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    return env

def head_ok(url):
    import urllib.request
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=2.5) as r:
            return r.status < 400
    except Exception:
        return False

# ---------------- Dev server ----------------
_DEV = None
_DEV_LOG = None
def start_dev():
    global _DEV, _DEV_LOG
    if _DEV and _DEV.poll() is None: return "running"
    log = DEV_LOGS/f"basic_{int(time.time())}.log"
    f = open(log, "a", encoding="utf-8", errors="replace")
    _DEV_LOG = log
    _DEV = subprocess.Popen(["python","current/server_wrapper.py"], cwd=str(REPO),
                            stdout=f, stderr=f, stdin=subprocess.DEVNULL, env=_env_utf8())
    return "started"

def stop_dev():
    global _DEV
    if _DEV and _DEV.poll() is None:
        _DEV.terminate()
        try: _DEV.wait(timeout=3)
        except Exception: _DEV.kill()
    _DEV = None; return "stopped"

def dev_health():
    return "OK" if head_ok(f"http://127.0.0.1:{DEV_PORT}") else "ISSUE"

# ---------------- Quick tunnel ----------------
_TUNNEL = None
_TUNNEL_LOG = None
def start_tunnel():
    global _TUNNEL, _TUNNEL_LOG
    if _TUNNEL and _TUNNEL.poll() is None: return "running"
    log = CF_LOGS/f"basic_{int(time.time())}.log"
    f = open(log, "a", encoding="utf-8", errors="replace")
    _TUNNEL_LOG = log
    _TUNNEL = subprocess.Popen(["cloudflared","tunnel","--url",f"http://127.0.0.1:{DEV_PORT}","--loglevel","debug"],
                               cwd=str(REPO), stdout=f, stderr=f, stdin=subprocess.DEVNULL)
    return "started"

def stop_tunnel():
    global _TUNNEL
    if _TUNNEL and _TUNNEL.poll() is None:
        _TUNNEL.terminate()
        try: _TUNNEL.wait(timeout=3)
        except Exception: _TUNNEL.kill()
    _TUNNEL = None; return "stopped"

def latest_tunnel_url():
    files = sorted(CF_LOGS.glob("basic_*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files: return None
    try:
        txt = files[0].read_text(encoding="utf-8", errors="replace")
        m = URL_PAT.search(txt)
        if m:
            URL_FILE.write_text(m.group(0), encoding="utf-8"); return m.group(0)
    except Exception:
        return None
    return None

# ---------------- Tracker ----------------
_TRK = None
_TRK_LOG = None
def start_tracker():
    global _TRK, _TRK_LOG
    if _TRK and _TRK.poll() is None: return "running"
    log = TRK_LOGS/f"basic_{int(time.time())}.log"
    f = open(log, "a", encoding="utf-8", errors="replace")
    _TRK_LOG = log
    script = REPO/"scripts"/"tracker"/"pal_tracker.py"
    if script.exists():
        cmd = ["python", str(script), "--port", str(TRACKER_PORT)]
    else:
        cmd = ["python", str(script)]  # fallback
    _TRK = subprocess.Popen(cmd, cwd=str(REPO), stdout=f, stderr=f, stdin=subprocess.DEVNULL, env=_env_utf8())
    return "started"

def stop_tracker():
    global _TRK
    if _TRK and _TRK.poll() is None:
        _TRK.terminate()
        try: _TRK.wait(timeout=3)
        except Exception: _TRK.kill()
    _TRK = None; return "stopped"

def tracker_health():
    return "OK" if head_ok(f"http://127.0.0.1:{TRACKER_PORT}") else "ISSUE"

# ---------------- Page ----------------
def tag(ok): return f"<span class='tag {'ok' if ok=='OK' else 'bad'}'>{ok}</span>"

def page():
    url = latest_tunnel_url() or "(no URL yet)"
    dev = dev_health()
    trk = tracker_health()
    html = f"""<!doctype html><html><head><meta charset='utf-8'><title>PAL Watchdog (Basic)</title>
<link rel="stylesheet" href="/static/style.css"></head>
<body>
<h1>PAL Watchdog</h1>
<p class="small">Basic dark UI • explicit Dev / Tracker / Quick Tunnel control.</p>

<div class="card"><b>Dev server</b> {tag(dev)}
<div style="margin-top:10px">
<form method="POST" action="/start-dev" style="display:inline"><button>Start Dev</button></form>
<form method="POST" action="/stop-dev" style="display:inline"><button>Stop Dev</button></form>
<a href="/tail?what=dev" style="margin-left:10px">Tail log</a>
</div></div>

<div class="card"><b>Tracker</b> {tag(trk)}
<div style="margin-top:6px">Open: <a href="http://127.0.0.1:{TRACKER_PORT}" target="_blank">http://127.0.0.1:{TRACKER_PORT}</a></div>
<div style="margin-top:10px">
<form method="POST" action="/start-tracker" style="display:inline"><button>Start Tracker</button></form>
<form method="POST" action="/stop-tracker" style="display:inline"><button>Stop Tracker</button></form>
<a href="/tail?what=trk" style="margin-left:10px">Tail log</a>
</div></div>

<div class="card"><b>Quick Tunnel</b>
<div style="margin-top:8px">URL: {url}</div>
<div style="margin-top:10px">
<form method="POST" action="/start-tunnel" style="display:inline"><button>Start Tunnel</button></form>
<form method="POST" action="/stop-tunnel" style="display:inline"><button>Stop Tunnel</button></form>
<form method="POST" action="/refresh-url" style="display:inline"><button>Refresh URL</button></form>
<a href="/tail?what=tunnel" style="margin-left:10px">Tail log</a>
</div></div>
</body></html>"""
    return html

class H(BaseHTTPRequestHandler):
    def _send(self, s, code=200, ctype="text/html; charset=utf-8"):
        self.send_response(code); self.send_header("Content-Type", ctype); self.end_headers()
        if isinstance(s, str): s = s.encode("utf-8")
        self.wfile.write(s)

    def do_GET(self):
        if self.path.startswith("/static/"):
            p = STATIC / self.path.split("/static/",1)[1]
            if p.exists():
                self._send(p.read_text(encoding="utf-8"), 200, "text/css; charset=utf-8"); return
            self._send("not found",404); return
        if self.path.startswith("/tail"):
            q = urlparse(self.path).query
            from urllib.parse import parse_qs
            w = parse_qs(q).get("what",[""])[0]
            fp = None
            if w=="dev": fp = _DEV_LOG
            elif w=="trk": fp = _TRK_LOG
            elif w=="tunnel": fp = _TUNNEL_LOG
            if fp and Path(fp).exists():
                txt = Path(fp).read_text(encoding="utf-8", errors="replace")
                return self._send(f"<html><body><pre>{txt[-20000:]}</pre><a href='/'>Back</a></body></html>")
            return self._send("<html><body><pre>No log yet</pre><a href='/'>Back</a></body></html>",404)
        self._send(page())

    def do_POST(self):
        ln = int(self.headers.get("content-length",0))
        _ = self.rfile.read(ln).decode("utf-8")
        if self.path == "/start-dev":
            start_dev(); time.sleep(1)
        elif self.path == "/stop-dev":
            stop_dev()
        elif self.path == "/start-tracker":
            start_tracker(); time.sleep(1)
        elif self.path == "/stop-tracker":
            stop_tracker()
        elif self.path == "/start-tunnel":
            start_tunnel(); time.sleep(1)
        elif self.path == "/stop-tunnel":
            stop_tunnel()
        elif self.path == "/refresh-url":
            latest_tunnel_url()
        self.send_response(303); self.send_header("Location","/"); self.end_headers()

def main():
    httpd = HTTPServer(("127.0.0.1", PORT), H)
    print(f"Basic Watchdog at http://127.0.0.1:{PORT}")
    httpd.serve_forever()

if __name__ == "__main__":
    main()

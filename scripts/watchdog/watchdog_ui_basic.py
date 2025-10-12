#!/usr/bin/env python3
import os, sys, re, json, time, subprocess, threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse
from pathlib import Path

REPO = Path(r"C:\_Repos\PersistentAssistant")
PORT = 9001
DEV_PORT = 8787
LOGS = REPO/"logs"; LOGS.mkdir(parents=True, exist_ok=True)
CF_LOGS = LOGS/"cloudflared"; CF_LOGS.mkdir(parents=True, exist_ok=True)
STATIC = REPO/"scripts"/"watchdog"/"static"
URL_PAT = re.compile(r"https://[A-Za-z0-9\-\.]+\.trycloudflare\.com")
URL_FILE = CF_LOGS/"basic_quicktunnel_url.txt"

def start_dev():
    # very basic: run server_wrapper.py
    return subprocess.Popen(["python","current/server_wrapper.py"], cwd=str(REPO),
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)

def head_ok(url):
    import urllib.request
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=2.5) as r:
            return r.status < 400
    except Exception:
        return False

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
        try:
            _TUNNEL.wait(timeout=3)
        except Exception:
            _TUNNEL.kill()
    _TUNNEL = None
    return "stopped"

def latest_tunnel_url():
    # scan latest log for trycloudflare URL
    files = sorted(CF_LOGS.glob("basic_*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files: return None
    try:
        txt = files[0].read_text(encoding="utf-8", errors="replace")
        m = URL_PAT.search(txt)
        if m:
            URL_FILE.write_text(m.group(0), encoding="utf-8")
            return m.group(0)
    except Exception:
        return None
    return None

def page():
    url = latest_tunnel_url() or "(no URL yet)"
    dev = "OK" if head_ok(f"http://127.0.0.1:{DEV_PORT}") else "ISSUE"
    html = f"""<!doctype html><html><head><meta charset='utf-8'><title>PAL Watchdog (Basic)</title>
<link rel="stylesheet" href="/static/style.css"></head>
<body>
<h1>PAL Watchdog</h1>
<p class="small">Basic dark UI • explicit Quick Tunnel control.</p>
<div class="card"><b>Dev server</b> <span class="tag {'ok' if dev=='OK' else 'bad'}">{dev}</span>
<div style="margin-top:10px">
<form method="POST" action="/start-dev" style="display:inline"><button>Start Dev</button></form>
</div></div>
<div class="card"><b>Quick Tunnel</b>
<div style="margin-top:8px">URL: {url}</div>
<div style="margin-top:10px">
<form method="POST" action="/start-tunnel" style="display:inline"><button>Start Tunnel</button></form>
<form method="POST" action="/stop-tunnel" style="display:inline"><button>Stop Tunnel</button></form>
<form method="POST" action="/refresh-url" style="display:inline"><button>Refresh URL</button></form>
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
        self._send(page())

    def do_POST(self):
        ln = int(self.headers.get("content-length",0))
        body = self.rfile.read(ln).decode("utf-8"); p = parse_qs(body)
        if self.path == "/start-dev":
            start_dev(); self.send_response(303); self.send_header("Location","/"); self.end_headers(); return
        if self.path == "/start-tunnel":
            start_tunnel(); time.sleep(1); self.send_response(303); self.send_header("Location","/"); self.end_headers(); return
        if self.path == "/stop-tunnel":
            stop_tunnel(); self.send_response(303); self.send_header("Location","/"); self.end_headers(); return
        if self.path == "/refresh-url":
            latest_tunnel_url(); self.send_response(303); self.send_header("Location","/"); self.end_headers(); return

def main():
    httpd = HTTPServer(("127.0.0.1", PORT), H)
    print(f"Basic Watchdog at http://127.0.0.1:{PORT}")
    httpd.serve_forever()

if __name__ == "__main__":
    main()

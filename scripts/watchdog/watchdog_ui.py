#!/usr/bin/env python3
import os, sys, json, time, threading, urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs
from pathlib import Path

sys.path.insert(0, str(Path(r"C:\_Repos\PersistentAssistant\scripts\config")))
import pal_settings  # type: ignore

REPO = Path(pal_settings.get("paths.repo_root"))
SET = pal_settings.load_settings()
PORT_UI = int(SET["ports"]["watchdog_ui"])

from scripts.watchdog.watchdog_core import start, stop, restart, initialize_all, loop, META, REPO as CORE_REPO  # type: ignore

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
small.m{{color:var(--muted)}}
"""

def page():
    cards = []
    for name, meta in META.items():
        ok = bool(meta.get("last_ok"))
        restarts = meta.get("restarts", 0)
        pid = meta.get("pid")
        tag = f"<span class='tag {'ok' if ok else 'bad'}'>{'OK' if ok else 'ISSUE'}</span>"
        cards.append(f"""
        <div class="card">
          <b>{name}</b> {tag}
          <div style="margin-top:8px;color:var(--muted)">
            pid:{pid} • last_ok:{meta.get('last_ok')} • restarts:{restarts}
          </div>
          <div style="margin-top:10px">
            <form method="POST" action="/ctl" style="display:inline">
              <input type="hidden" name="service" value="{name}">
              <button name="action" value="start">Start</button>
              <button name="action" value="stop">Stop</button>
              <button name="action" value="restart">Restart</button>
            </form>
            {"<a href='/log?service="+name+"'>Tail log</a>" if meta.get("logfile") else ""}
          </div>
        </div>
        """)
    controls = """
    <div class="card">
      <b>Controls</b><br>
      <form method="POST" action="/init" style="display:inline"><button>Initialize All</button></form>
      <form method="POST" action="/autostart" style="display:inline;margin-left:10px"><button>Apply Autostart Setting</button></form>
      <form method="POST" action="/smoke" style="display:inline;margin-left:10px"><button>Run Smoke</button></form>
    </div>
    """
    return f"<html><head><meta charset='utf-8'><title>PAL Watchdog</title><style>{CSS}</style></head><body><h2>PAL Watchdog</h2><p class='small'>Lifecycle manager (dark mode).</p>{''.join(cards)}{controls}</body></html>"

class H(BaseHTTPRequestHandler):
    def _send(self, html, code=200, ctype="text/html; charset=utf-8"):
        self.send_response(code); self.send_header("Content-type", ctype); self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def do_GET(self):
        if self.path.startswith("/log"):
            from urllib.parse import urlparse, parse_qs
            q = parse_qs(urlparse(self.path).query)
            svc = q.get("service", [""])[0]
            meta = META.get(svc, {}); fp = meta.get("logfile")
            if fp and Path(fp).exists():
                txt = Path(fp).read_text(encoding="utf-8", errors="replace")
                self._send(f"<html><body><pre>{txt[-20000:]}</pre><a href='/'>Back</a></body></html>"); return
            self._send("<html><body><pre>No log</pre><a href='/'>Back</a></body></html>",404); return
        self._send(page())

    def do_POST(self):
        ln = int(self.headers.get("content-length", 0))
        body = self.rfile.read(ln).decode("utf-8"); p = parse_qs(body)
        if self.path == "/init":
            threading.Thread(target=initialize_all, daemon=True).start()
            self.send_response(303); self.send_header("Location","/"); self.end_headers(); return
        if self.path == "/ctl":
            svc = p.get("service", [""])[0]; act = p.get("action", [""])[0]
            if act == "start": start(svc)
            elif act == "stop": stop(svc)
            elif act == "restart": restart(svc)
            self.send_response(303); self.send_header("Location","/"); self.end_headers(); return
        if self.path == "/smoke":
            from scripts.watchdog.watchdog_core import run_smoke_and_commit  # type: ignore
            threading.Thread(target=run_smoke_and_commit, daemon=True).start()
            self.send_response(303); self.send_header("Location","/"); self.end_headers(); return
        if self.path == "/autostart":
            # apply current setting by registering task if enabled
            if pal_settings.get("autostart.enabled"):
                tn = pal_settings.get("autostart.task_name","PAL_Watchdog")
                ps1 = CORE_REPO / "scripts" / "autostart" / "register_watchdog_task.ps1"
                cmd = ["powershell","-ExecutionPolicy","Bypass","-File", str(ps1), "-TaskName", tn]
                subprocess = __import__("subprocess")
                subprocess.run(cmd, cwd=str(CORE_REPO), check=False)
            self.send_response(303); self.send_header("Location","/"); self.end_headers(); return

def main():
    # start heartbeat loop in bg
    threading.Thread(target=loop, daemon=True).start()
    httpd = HTTPServer(("127.0.0.1", PORT_UI), H)
    print(f"Watchdog UI (lifecycle) at http://127.0.0.1:{PORT_UI}")
    httpd.serve_forever()

if __name__ == "__main__":
    main()

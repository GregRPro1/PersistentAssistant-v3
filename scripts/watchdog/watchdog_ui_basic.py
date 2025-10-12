#!/usr/bin/env python3
import os, sys, re, json, time, subprocess, threading, urllib.parse
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
from pathlib import Path

CFG_PATH = Path(r"C:\_Repos\PersistentAssistant\config\pal_settings.yaml")

def load_settings(path: Path):
    # Prefer PyYAML if available, otherwise use a tolerant two-level parser.
    data = {}
    if path.exists():
        try:
            import yaml  # type: ignore
            y = yaml.safe_load(path.read_text(encoding="utf-8"))
            if isinstance(y, dict):
                return y
        except Exception:
            pass
    # Fallback tiny parser
    out = {}; stack = [(0, out)]
    if not path.exists(): return {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip("\r\n")
        if not line.strip() or line.lstrip().startswith("#"): continue
        indent = len(line) - len(line.lstrip(' '))
        while stack and indent < stack[-1][0]:
            stack.pop()
        cur = stack[-1][1]
        if ":" in line:
            k, v = line.lstrip().split(":",1)
            k = k.strip(); v = v.strip()
            if v == "":
                new_map = {}
                cur[k] = new_map
                stack.append((indent+2, new_map))
            else:
                if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
                    v = v[1:-1]
                cur[k] = v
    return out

SET = load_settings(CFG_PATH)
paths = SET.get("paths", {})
ports = SET.get("ports", {})
wa    = SET.get("whatsapp", {})

REPO = Path(paths.get("repo_root", r"C:\_Repos\PersistentAssistant"))
PORT = int(ports.get("watchdog_ui", 9001))
DEV_PORT = int(ports.get("dev_server", 8787))
TRACKER_PORT = int(ports.get("tracker", 9002))

# Critically: *only* use config value for tracker_script; if missing, treat invalid (no fallback).
TRACKER_SCRIPT_STR = paths.get("tracker_script", "")
TRACKER_SCRIPT = Path(TRACKER_SCRIPT_STR) if TRACKER_SCRIPT_STR else Path("")
WA_NUMBER = str(wa.get("number","")).strip()

LOGS = REPO/"logs"; LOGS.mkdir(parents=True, exist_ok=True)
DEV_LOGS = LOGS/"dev_server"; DEV_LOGS.mkdir(parents=True, exist_ok=True)
TRK_LOGS = LOGS/"tracker"; TRK_LOGS.mkdir(parents=True, exist_ok=True)
CF_LOGS = LOGS/"cloudflared"; CF_LOGS.mkdir(parents=True, exist_ok=True)
STATIC = REPO/"scripts"/"watchdog"/"static"

URL_PAT = re.compile(r"https://[A-Za-z0-9\-\.]+\.trycloudflare\.com")
HB = {"dev": None, "tracker": None}
STATUS = {"dev_tunnel":"idle", "trk_tunnel":"idle"}  # idle|starting|ready|stopped

def _env_utf8():
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    sep = ";" if os.name == "nt" else ":"
    env["PYTHONPATH"] = (env.get("PYTHONPATH","") + (sep if env.get("PYTHONPATH") else "") + str(REPO))
    return env

def head_ok(url):
    import urllib.request
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=2.5) as r:
            return r.status < 400
    except Exception:
        return False

# ---------- Dev server ----------
_DEV=None; _DEV_LOG=None
def start_dev_bg():
    global _DEV, _DEV_LOG
    if _DEV and _DEV.poll() is None: return
    log = DEV_LOGS/f"basic_{int(time.time())}.log"
    f = open(log, "a", encoding="utf-8", errors="replace")
    _DEV_LOG = str(log)
    _DEV = subprocess.Popen(["python","current/server_wrapper.py"], cwd=str(REPO),
                            stdout=f, stderr=f, stdin=subprocess.DEVNULL, env=_env_utf8())
def stop_dev_bg():
    global _DEV
    if _DEV and _DEV.poll() is None:
        _DEV.terminate()
        try: _DEV.wait(timeout=3)
        except Exception: _DEV.kill()
    _DEV=None
def dev_health():
    ok = head_ok(f"http://127.0.0.1:{DEV_PORT}"); HB["dev"]=time.time(); return ok

# ---------- Tunnels ----------
_TUN_DEV=None; _TUN_DEV_LOG=None; _URL_DEV=None
_TUN_TRK=None; _TUN_TRK_LOG=None; _URL_TRK=None

def _start_tunnel_async(port, label):
    # Run in background so UI returns quickly
    def run():
        global _TUN_DEV,_TUN_DEV_LOG,_TUN_TRK,_TUN_TRK_LOG
        log = CF_LOGS/f"{label}_{int(time.time())}.log"
        STATUS[f"{'dev' if label=='dev' else 'trk'}_tunnel"] = "starting"
        f = open(log, "a", encoding="utf-8", errors="replace")
        p = subprocess.Popen(["cloudflared","tunnel","--url",f"http://127.0.0.1:{port}","--loglevel","debug"],
                             cwd=str(REPO), stdout=f, stderr=f, stdin=subprocess.DEVNULL)
        if label=="dev":
            _TUN_DEV = p; _TUN_DEV_LOG = str(log)
        else:
            _TUN_TRK = p; _TUN_TRK_LOG = str(log)
        # Give cloudflared some time to print URL; mark ready when URL appears
        for _ in range(20):  # ~10s @0.5s
            time.sleep(0.5)
            refresh_urls()
            url = _URL_DEV if label=="dev" else _URL_TRK
            if url:
                STATUS[f"{'dev' if label=='dev' else 'trk'}_tunnel"] = "ready"
                return
        # No URL yet, leave as starting (UI will show and you can click Refresh)
    threading.Thread(target=run, daemon=True).start()

def _stop_tunnel(which):
    global _TUN_DEV,_TUN_TRK
    p = _TUN_DEV if which=="dev" else _TUN_TRK
    if p and p.poll() is None:
        p.terminate()
        try: p.wait(timeout=3)
        except Exception: p.kill()
    if which=="dev":
        _TUN_DEV=None; STATUS["dev_tunnel"]="stopped"
    else:
        _TUN_TRK=None; STATUS["trk_tunnel"]="stopped"

def _extract_url(log_path: Path):
    try:
        txt = Path(log_path).read_text(encoding="utf-8", errors="replace")
        m = URL_PAT.search(txt)
        return m.group(0) if m else None
    except Exception:
        return None

def refresh_urls():
    global _URL_DEV,_URL_TRK
    if _TUN_DEV_LOG and Path(_TUN_DEV_LOG).exists():
        _URL_DEV = _extract_url(_TUN_DEV_LOG)
    if _TUN_TRK_LOG and Path(_TUN_TRK_LOG).exists():
        _URL_TRK = _extract_url(_TUN_TRK_LOG)

# ---------- Tracker ----------
_TRK=None; _TRK_LOG=None
def start_tracker_bg():
    global _TRK,_TRK_LOG
    if _TRK and _TRK.poll() is None: return
    if not TRACKER_SCRIPT or not TRACKER_SCRIPT.exists(): return
    log = TRK_LOGS/f"basic_{int(time.time())}.log"
    f = open(log, "a", encoding="utf-8", errors="replace"); _TRK_LOG=str(log)
    cmd = ["python", str(TRACKER_SCRIPT), "--port", str(TRACKER_PORT)]
    _TRK = subprocess.Popen(cmd, cwd=str(REPO), stdout=f, stderr=f, stdin=subprocess.DEVNULL, env=_env_utf8())
def stop_tracker_bg():
    global _TRK
    if _TRK and _TRK.poll() is None:
        _TRK.terminate()
        try: _TRK.wait(timeout=3)
        except Exception: _TRK.kill()
    _TRK=None
def tracker_health():
    ok = head_ok(f"http://127.0.0.1:{TRACKER_PORT}"); HB["tracker"]=time.time(); return ok

# ---------- WhatsApp helpers ----------
def wa_link(url):
    if not url: return ""
    base = "https://wa.me/"
    if WA_NUMBER: base += WA_NUMBER
    text = urllib.parse.quote(f"PAL URL: {url}")
    return f"{base}?text={text}"

# ---------- UI helpers ----------
def tag(ok): return f"<span class='tag {'ok' if ok else 'bad'}'>{'OK' if ok else 'ISSUE'}</span>"
def ago(ts): 
    if not ts: return "never"
    s=int(time.time()-ts); return f"{s}s ago" if s<60 else f"{s//60}m ago"
def pill(state):
    colors={"idle":"#777","starting":"#d4b106","ready":"#52c41a","stopped":"#d32029"}
    return f"<span style='background:{colors.get(state,'#777')};color:#111;padding:2px 6px;border-radius:10px;font-size:12px'>{state}</span>"

def settings_page(msg=""):
    num = WA_NUMBER
    html = f"""<!doctype html><html><head><meta charset='utf-8'><title>Settings</title>
<link rel="stylesheet" href="/static/style.css"></head><body>
<h1>Settings</h1>
<p class="small">Edit WhatsApp destination (E.164). Example UK: 447700900123</p>
<form method="POST" action="/save-settings">
<label>whatsapp.number</label><br>
<input name="wa_number" value="{num}" style="min-width:320px" />
<button style="margin-left:8px">Save</button>
</form>
<p class="small">{msg}</p>
<p><a href="/">Back</a></p>
</body></html>"""
    return html

def page():
    refresh_urls()
    dev_ok = dev_health(); trk_ok = tracker_health()
    trk_info = f"Tracker script: {TRACKER_SCRIPT}" if (TRACKER_SCRIPT and TRACKER_SCRIPT.exists()) else "<span style='color:#ff8b8b'>Tracker script path invalid — update config/pal_settings.yaml</span><br><small class='m'>Currently parsed path: {}</small>".format(TRACKER_SCRIPT if TRACKER_SCRIPT_STR else "(empty)")
    auto = "<meta http-equiv='refresh' content='2'>" if (STATUS["dev_tunnel"]=='starting' or STATUS["trk_tunnel"]=='starting') else ""
    html = f"""<!doctype html><html><head><meta charset='utf-8'><title>PAL Watchdog (Basic)</title>
{auto}
<link rel="stylesheet" href="/static/style.css"></head>
<body>
<h1>PAL Watchdog</h1>
<p class="small">Dark, fast, minimal. Config-driven paths. Separate tunnels for Dev and Tracker. <a href="/settings">Settings</a></p>

<div class="card"><b>Dev server</b> {tag(dev_ok)} <small class="m">last hb: {ago(HB['dev'])}</small>
<div style="margin-top:10px">
<form method="POST" action="/start-dev" style="display:inline"><button>Start Dev</button></form>
<form method="POST" action="/stop-dev" style="display:inline"><button>Stop Dev</button></form>
<a href="/tail?what=dev" style="margin-left:10px">Tail log</a>
</div></div>

<div class="card"><b>Dev Tunnel</b> {pill(STATUS['dev_tunnel'])}
<div style="margin-top:6px">URL: { _URL_DEV or '(none yet)' } {'• <a target="_blank" href="'+wa_link(_URL_DEV)+'">WhatsApp</a>' if _URL_DEV else ''}</div>
<div style="margin-top:10px">
<form method="POST" action="/start-tunnel-dev" style="display:inline"><button>Start Dev Tunnel</button></form>
<form method="POST" action="/stop-tunnel-dev" style="display:inline"><button>Stop Dev Tunnel</button></form>
<form method="POST" action="/refresh-url" style="display:inline"><button>Refresh URL</button></form>
<a href="/tail?what=tunnel-dev" style="margin-left:10px">Tail log</a>
</div></div>

<div class="card"><b>Tracker</b> {tag(trk_ok)} <small class="m">last hb: {ago(HB['tracker'])}</small>
<div style="margin-top:6px">{trk_info}</div>
<div style="margin-top:10px">
<form method="POST" action="/start-tracker" style="display:inline"><button>Start Tracker</button></form>
<form method="POST" action="/stop-tracker" style="display:inline"><button>Stop Tracker</button></form>
<a href="/tail?what=trk" style="margin-left:10px">Tail log</a>
</div></div>

<div class="card"><b>Tracker Tunnel</b> {pill(STATUS['trk_tunnel'])}
<div style="margin-top:6px">URL: { _URL_TRK or '(none yet)' } {'• <a target="_blank" href="'+wa_link(_URL_TRK)+'">WhatsApp</a>' if _URL_TRK else ''}</div>
<div class="small" style="margin-top:4px">Send the <b>Tracker Tunnel URL</b> to your phone.</div>
<div style="margin-top:10px">
<form method="POST" action="/start-tunnel-trk" style="display:inline"><button>Start Tracker Tunnel</button></form>
<form method="POST" action="/stop-tunnel-trk" style="display:inline"><button>Stop Tracker Tunnel</button></form>
<form method="POST" action="/refresh-url" style="display:inline"><button>Refresh URL</button></form>
<a href="/tail?what=tunnel-trk" style="margin-left:10px">Tail log</a>
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
            if p.exists(): return self._send(p.read_text(encoding="utf-8"), 200, "text/css; charset=utf-8")
            return self._send("not found",404)
        if self.path.startswith("/tail"):
            q = urlparse(self.path).query; w = parse_qs(q).get("what",[""])[0]
            fp = {"dev": _DEV_LOG, "trk": _TRK_LOG, "tunnel-dev": _TUN_DEV_LOG, "tunnel-trk": _TUN_TRK_LOG}.get(w)
            if fp and Path(fp).exists():
                txt = Path(fp).read_text(encoding="utf-8", errors="replace")
                return self._send(f"<html><body><pre>{txt[-20000:]}</pre><a href='/'>Back</a></body></html>")
            return self._send("<html><body><pre>No log yet</pre><a href='/'>Back</a></body></html>",404)
        if self.path.startswith("/settings"):
            return self._send(settings_page())
        self._send(page())

    def do_POST(self):
        ln = int(self.headers.get("content-length",0))
        body = self.rfile.read(ln).decode("utf-8"); p = parse_qs(body)
        def bg(fn): threading.Thread(target=fn, daemon=True).start()
        if self.path == "/start-dev": bg(start_dev_bg)
        elif self.path == "/stop-dev": bg(stop_dev_bg)
        elif self.path == "/start-tracker": bg(start_tracker_bg)
        elif self.path == "/stop-tracker": bg(stop_tracker_bg)
        elif self.path == "/start-tunnel-dev": STATUS["dev_tunnel"]="starting"; bg(lambda: _start_tunnel_async(DEV_PORT,"dev"))
        elif self.path == "/stop-tunnel-dev": _stop_tunnel("dev")
        elif self.path == "/start-tunnel-trk": STATUS["trk_tunnel"]="starting"; bg(lambda: _start_tunnel_async(TRACKER_PORT,"trk"))
        elif self.path == "/stop-tunnel-trk": _stop_tunnel("trk")
        elif self.path == "/refresh-url": refresh_urls()
        elif self.path == "/save-settings":
            num = p.get("wa_number",[""])[0].strip()
            # Persist by editing CFG file; keep structure minimal (only whatsapp.number)
            lines = []
            wrote=False; in_wa=False
            if CFG_PATH.exists():
                for line in CFG_PATH.read_text(encoding="utf-8").splitlines():
                    if line.strip().startswith("whatsapp:"):
                        in_wa=True; lines.append(line); continue
                    if in_wa and re.match(r"^\S", line):  # left section
                        if not wrote:
                            lines.append(f"  number: {num}")
                            wrote=True
                        in_wa=False
                    if in_wa and line.strip().startswith("number:"):
                        line = re.sub(r"number:\s*.*$", f"number: {num}", line)
                        wrote=True
                    lines.append(line)
                if in_wa and not wrote:
                    lines.append(f"  number: {num}")
            else:
                lines = ["whatsapp:","  number: "+num]
            CFG_PATH.write_text("\n".join(lines)+"\n", encoding="utf-8")
            # Reload number
            global WA_NUMBER
            WA_NUMBER = num
            return self._send(settings_page("Saved."))
        self.send_response(303); self.send_header("Location","/"); self.end_headers()

def main():
    httpd = ThreadingHTTPServer(("127.0.0.1", PORT), H)
    print(f"Basic Watchdog at http://127.0.0.1:{PORT}")
    httpd.serve_forever()

if __name__ == "__main__":
    main()

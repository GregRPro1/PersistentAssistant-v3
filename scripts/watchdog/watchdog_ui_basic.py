#!/usr/bin/env python3
import os, sys, re, json, time, subprocess, threading, urllib.parse
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
from pathlib import Path

# -------- Settings --------
CFG_PATH = Path(r"C:\_Repos\PersistentAssistant\config\pal_settings.yaml")

def load_yaml_map(path: Path):
    """
    Minimal YAML loader:
    - top-level keys -> nested dicts
    - supports two-level mapping with indentation (2 spaces or more)
    - preserves backslashes and spaces in values
    - ignores comments and blank lines
    """
    data = {}
    stack = [(0, data)]
    if not path.exists():
        return {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip("\r\n")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(' '))
        while stack and indent < stack[-1][0]:
            stack.pop()
        current = stack[-1][1]

        if ":" in line:
            k, v = line.lstrip().split(":", 1)
            k = k.strip()
            v = v.strip()
            if v == "":  # new nested map
                new_map = {}
                current[k] = new_map
                stack.append((indent+2, new_map))
            else:
                # strip only outer quotes
                if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
                    v = v[1:-1]
                current[k] = v
    return data

SET = load_yaml_map(CFG_PATH)

REPO = Path(SET.get("paths",{}).get("repo_root", r"C:\_Repos\PersistentAssistant"))
PORT = int(SET.get("ports",{}).get("watchdog_ui", "9001") or "9001")
DEV_PORT = int(SET.get("ports",{}).get("dev_server", "8787") or "8787")
TRACKER_PORT = int(SET.get("ports",{}).get("tracker", "9002") or "9002")
TRACKER_SCRIPT_STR = SET.get("paths",{}).get("tracker_script", r"C:\_Repos\PersistentAssistant\scripts\tracker\pal_tracker.py")
TRACKER_SCRIPT = Path(TRACKER_SCRIPT_STR)

WA = SET.get("whatsapp",{})
WA_NUMBER = WA.get("number","")
WA_CLOUD = {
    "enabled": (str(WA.get("cloud_api_enabled","false")).lower() == "true"),
    "token": WA.get("cloud_access_token",""),
    "phone_id": WA.get("cloud_phone_number_id",""),
    "to": WA.get("cloud_to_number",""),
}

# -------- Paths/Logs --------
LOGS = REPO/"logs"; LOGS.mkdir(parents=True, exist_ok=True)
DEV_LOGS = LOGS/"dev_server"; DEV_LOGS.mkdir(parents=True, exist_ok=True)
TRK_LOGS = LOGS/"tracker"; TRK_LOGS.mkdir(parents=True, exist_ok=True)
CF_LOGS = LOGS/"cloudflared"; CF_LOGS.mkdir(parents=True, exist_ok=True)
STATIC = REPO/"scripts"/"watchdog"/"static"

URL_PAT = re.compile(r"https://[A-Za-z0-9\-\.]+\.trycloudflare\.com")
HB = {"dev": None, "tracker": None}

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
_DEV = None; _DEV_LOG = None
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
    _DEV = None

def dev_health():
    ok = head_ok(f"http://127.0.0.1:{DEV_PORT}"); HB["dev"] = time.time(); return ok

# ---------- Quick tunnels ----------
_TUN_DEV = None; _TUN_DEV_LOG = None; _URL_DEV = None
_TUN_TRK = None; _TUN_TRK_LOG = None; _URL_TRK = None

def _start_tunnel(port, label):
    global _TUN_DEV, _TUN_DEV_LOG, _TUN_TRK, _TUN_TRK_LOG
    log = CF_LOGS/f"{label}_{int(time.time())}.log"
    f = open(log, "a", encoding="utf-8", errors="replace")
    p = subprocess.Popen(["cloudflared","tunnel","--url",f"http://127.0.0.1:{port}","--loglevel","debug"],
                         cwd=str(REPO), stdout=f, stderr=f, stdin=subprocess.DEVNULL)
    if label=="dev":
        _TUN_DEV = p; _TUN_DEV_LOG = str(log)
    else:
        _TUN_TRK = p; _TUN_TRK_LOG = str(log)

def _stop_tunnel(which):
    global _TUN_DEV, _TUN_TRK
    p = _TUN_DEV if which=="dev" else _TUN_TRK
    if p and p.poll() is None:
        p.terminate()
        try: p.wait(timeout=3)
        except Exception: p.kill()
    if which=="dev": _TUN_DEV = None
    else: _TUN_TRK = None

def _extract_url(log_path: Path):
    try:
        txt = Path(log_path).read_text(encoding="utf-8", errors="replace")
        m = URL_PAT.search(txt)
        return m.group(0) if m else None
    except Exception:
        return None

def refresh_urls():
    global _URL_DEV, _URL_TRK
    if _TUN_DEV_LOG and Path(_TUN_DEV_LOG).exists():
        _URL_DEV = _extract_url(_TUN_DEV_LOG)
    if _TUN_TRK_LOG and Path(_TUN_TRK_LOG).exists():
        _URL_TRK = _extract_url(_TUN_TRK_LOG)

# ---------- Tracker ----------
_TRK = None; _TRK_LOG = None
def start_tracker_bg():
    global _TRK, _TRK_LOG
    if _TRK and _TRK.poll() is None: return
    if not TRACKER_SCRIPT.exists():
        return
    log = TRK_LOGS/f"basic_{int(time.time())}.log"
    f = open(log, "a", encoding="utf-8", errors="replace"); _TRK_LOG = str(log)
    cmd = ["python", str(TRACKER_SCRIPT), "--port", str(TRACKER_PORT)]
    _TRK = subprocess.Popen(cmd, cwd=str(REPO), stdout=f, stderr=f, stdin=subprocess.DEVNULL, env=_env_utf8())

def stop_tracker_bg():
    global _TRK
    if _TRK and _TRK.poll() is None:
        _TRK.terminate()
        try: _TRK.wait(timeout=3)
        except Exception: _TRK.kill()
    _TRK = None

def tracker_health():
    ok = head_ok(f"http://127.0.0.1:{TRACKER_PORT}"); HB["tracker"] = time.time(); return ok

# ---------- WhatsApp helpers ----------
def share_wa_link(url):
    if not url: return ""
    base = "https://wa.me/"
    if WA_NUMBER := WA.get("number",""):
        base += WA_NUMBER
    text = urllib.parse.quote(f"PAL URL: {url}")
    return f"{base}?text={text}"

def share_via_cloud_api(url):
    if not (WA_CLOUD["enabled"] and WA_CLOUD["token"] and WA_CLOUD["phone_id"] and WA_CLOUD["to"]):
        return False, "Cloud API not configured"
    try:
        import urllib.request, json as _json
        req = urllib.request.Request(
            f"https://graph.facebook.com/v19.0/{WA_CLOUD['phone_id']}/messages",
            method="POST",
            headers={
                "Authorization": f"Bearer {WA_CLOUD['token']}",
                "Content-Type": "application/json"
            },
            data=_json.dumps({
                "messaging_product": "whatsapp",
                "to": WA_CLOUD["to"],
                "type": "text",
                "text": {"body": f"PAL URL: {url}"}
            }).encode("utf-8")
        )
        with urllib.request.urlopen(req, timeout=8) as r:
            return 200 <= r.status < 300, f"HTTP {r.status}"
    except Exception as e:
        return False, str(e)

# ---------- UI ----------
def tag(ok): return f"<span class='tag {'ok' if ok else 'bad'}'>{'OK' if ok else 'ISSUE'}</span>"
def ago(ts):
    if not ts: return "never"
    s=int(time.time()-ts); 
    return f"{s}s ago" if s<60 else f"{s//60}m ago"

def page():
    refresh_urls()
    dev_ok = dev_health(); trk_ok = tracker_health()
    trk_info = f"Tracker script: {TRACKER_SCRIPT}" if TRACKER_SCRIPT.exists() else "<span style='color:#ff8b8b'>Tracker script path invalid — update config/pal_settings.yaml</span><br><small class='m'>Currently parsed path: {}</small>".format(TRACKER_SCRIPT)
    html = f"""<!doctype html><html><head><meta charset='utf-8'><title>PAL Watchdog (Basic)</title>
<link rel="stylesheet" href="/static/style.css"></head>
<body>
<h1>PAL Watchdog</h1>
<p class="small">Dark, fast, minimal. Config-driven paths. Separate tunnels for Dev and Tracker.</p>

<div class="card"><b>Dev server</b> {tag(dev_ok)} <small class="m">last hb: {ago(HB['dev'])}</small>
<div style="margin-top:10px">
<form method="POST" action="/start-dev" style="display:inline"><button>Start Dev</button></form>
<form method="POST" action="/stop-dev" style="display:inline"><button>Stop Dev</button></form>
<a href="/tail?what=dev" style="margin-left:10px">Tail log</a>
</div></div>

<div class="card"><b>Dev Tunnel</b>
<div style="margin-top:6px">URL: { _URL_DEV or '(none yet)' } {'• <a target="_blank" href="'+share_wa_link(_URL_DEV)+'">WhatsApp</a>' if _URL_DEV else ''}</div>
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

<div class="card"><b>Tracker Tunnel</b>
<div style="margin-top:6px">URL: { _URL_TRK or '(none yet)' } {'• <a target="_blank" href="'+share_wa_link(_URL_TRK)+'">WhatsApp</a>' if _URL_TRK else ''}</div>
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
        self._send(page())

    def do_POST(self):
        ln = int(self.headers.get("content-length",0))
        body = self.rfile.read(ln).decode("utf-8"); p = parse_qs(body)
        def bg(fn): threading.Thread(target=fn, daemon=True).start()
        if self.path == "/start-dev": bg(start_dev_bg)
        elif self.path == "/stop-dev": bg(stop_dev_bg)
        elif self.path == "/start-tracker": bg(start_tracker_bg)
        elif self.path == "/stop-tracker": bg(stop_tracker_bg)
        elif self.path == "/start-tunnel-dev": bg(lambda: _start_tunnel(int(SET.get("ports",{}).get("dev_server", DEV_PORT)), "dev"))
        elif self.path == "/stop-tunnel-dev": bg(lambda: _stop_tunnel("dev"))
        elif self.path == "/start-tunnel-trk": bg(lambda: _start_tunnel(int(SET.get("ports",{}).get("tracker", TRACKER_PORT)), "trk"))
        elif self.path == "/stop-tunnel-trk": bg(lambda: _stop_tunnel("trk"))
        elif self.path == "/refresh-url": refresh_urls()
        elif self.path == "/wa-cloud":
            which = p.get("which",["dev"])[0]
            url = _URL_DEV if which=="dev" else _URL_TRK
            share_via_cloud_api(url)
        self.send_response(303); self.send_header("Location","/"); self.end_headers()

def main():
    httpd = ThreadingHTTPServer(("127.0.0.1", PORT), H)
    print(f"Basic Watchdog at http://127.0.0.1:{PORT}")
    httpd.serve_forever()

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
from __future__ import annotations
import os, sys, time, json, subprocess, threading, signal, urllib.request, traceback, argparse
from http.server import BaseHTTPRequestHandler, HTTPServer

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LOG_DIR = os.path.join(REPO, "reports", "ops")
os.makedirs(LOG_DIR, exist_ok=True)
LOG = os.path.join(LOG_DIR, "supervisor.log")
STATS = os.path.join(LOG_DIR, "supervisor_stats.json")

CTRL_HOST, CTRL_PORT = "127.0.0.1", 6060
CHECK_INTERVAL = 5
PY = sys.executable or "python"

def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S"); line = f"{ts} {msg}"
    print(line, flush=True)
    try:
        with open(LOG, "a", encoding="utf-8") as f: f.write(line+"\n")
    except: pass

# ignore Ctrl+C / console ctrl events
try: signal.signal(signal.SIGINT, lambda *_: log("[WARN] SIGINT ignored"))
except: pass
try:
    import ctypes
    from ctypes import wintypes
    PH = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.DWORD)
    def _ctrl(t):
        if t in (0,1): log("[WARN] Console CTRL event ignored"); return True
        return False
    ctypes.windll.kernel32.SetConsoleCtrlHandler(PH(_ctrl), True)
except: pass

ALL_SERVICES = {
    "heartbeat":     [PY, "scripts/ops/emit_bridge_heartbeat.py", "--loop", "10"],
    "planrefresher": [PY, "scripts/utils/plan_refresher.py", "--loop", "10"],
    "bridgeui":      [PY, "scripts/bridge_ui/app.py", "--host", "0.0.0.0", "--port", "5070"],
    "phonesvc":      [PY, "scripts/phone/phone_bridge.py"],
    "tunnelsvc":     ["powershell", "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden", "-File", "scripts/tunnel/run_cloudflared_quick.ps1"],
}

state, restart_counts = {}, {}

def save_stats():
    try:
        with open(STATS,"w",encoding="utf-8") as f:
            json.dump({"restart_counts": restart_counts, "updated_ts": time.time()}, f, indent=2)
    except Exception as e: log(f"[ERR] save_stats: {e}")

def spawn(cmd):
    try:
        # CREATE_NO_WINDOW
        CREATE_NO_WINDOW = 0x08000000
        si = None
        if os.name == "nt":
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = 0
        return subprocess.Popen(cmd, cwd=REPO, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                creationflags=(CREATE_NO_WINDOW if os.name=="nt" else 0), startupinfo=si)
    except Exception as e:
        log(f"[ERR] spawn failed: {' '.join(cmd)} -> {e}")
        return None

def start(name, services):
    if state[name]["alive"]: return
    p = spawn(services[name])
    if p and getattr(p, "pid", None):
        state[name].update(pid=p.pid, alive=True, misses=0)
        log(f"[START] {name} PID={p.pid} CMD={' '.join(services[name])}")
    else:
        state[name].update(pid=None, alive=False); log(f"[DOWN] {name} failed to start")

def stop(name):
    pid = state[name]["pid"]; 
    if not pid: state[name].update(alive=False); return
    try: os.kill(pid, signal.SIGTERM)
    except: pass
    state[name].update(pid=None, alive=False, misses=0); log(f"[OK] stopped {name}")

def restart(name, services):
    stop(name); time.sleep(0.4); start(name, services)
    restart_counts[name] = restart_counts.get(name,0)+1; log(f"[RESTART] {name}"); save_stats()

def is_alive(pid):
    if not pid: return False
    try: os.kill(pid, 0); return True
    except: return False

def http_ok(url, timeout=1.0):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r: return 200 <= r.status < 300
    except: return False

def singleton_guard():
    if http_ok(f"http://{CTRL_HOST}:{CTRL_PORT}/health"): 
        log("[WARN] Another supervisor instance active — exiting."); sys.exit(0)

class H(BaseHTTPRequestHandler):
    def _json(self, code=200, obj=None):
        b = json.dumps(obj or {}).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type","application/json")
        self.send_header("Access-Control-Allow-Origin","*")
        self.send_header("Access-Control-Allow-Methods","GET,POST,OPTIONS")
        self.end_headers(); self.wfile.write(b)
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin","*")
        self.send_header("Access-Control-Allow-Methods","GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers","Content-Type")
        self.end_headers()
    def do_GET(self):
        if self.path=="/status": return self._json(200, {"timestamp":time.time(),"healthy":True,"services":state})
        if self.path=="/health": return self._json(200, {"ok":True,"ts":time.time()})
        if self.path=="/": 
            html="<html><body><h3>PAL Supervisor Control</h3><p><a href='/status'>/status</a> | <a href='/health'>/health</a></p></body></html>"
            self.send_response(200); self.end_headers(); self.wfile.write(html.encode()); return
        return self._json(404, {"error":"not found"})
    def do_POST(self):
        from urllib.parse import urlparse, parse_qs
        if self.path.startswith("/control"):
            q = parse_qs(urlparse(self.path).query)
            svc=(q.get("service") or [""])[0]; act=(q.get("action") or [""])[0]
            if svc=="all" and act=="restart": 
                [restart(n,SERVICES_ACTIVE) for n in list(state.keys())]; return self._json(200, {"ok":True})
            if svc in state and act=="restart": restart(svc,SERVICES_ACTIVE); return self._json(200, {"ok":True})
            return self._json(400, {"error":"bad request"})
        return self._json(404, {"error":"not found"})

def http_server_thread():
    try:
        httpd = HTTPServer((CTRL_HOST, CTRL_PORT), H)
        log(f"[CTRL] Listening on http://{CTRL_HOST}:{CTRL_PORT}"); httpd.serve_forever()
    except Exception as e:
        log(f"[ERR] control server thread: {e}\n{traceback.format_exc()}")

def monitor_thread():
    try:
        for n in SERVICES_ACTIVE: start(n, SERVICES_ACTIVE)
        while True:
            try:
                for n in list(SERVICES_ACTIVE.keys()):
                    pid = state[n]["pid"]; alive = is_alive(pid)
                    if not alive:
                        if state[n]["alive"]: log(f"[DOWN] {n}")
                        state[n]["alive"] = False; restart(n, SERVICES_ACTIVE); continue
                    state[n]["alive"] = True
                time.sleep(CHECK_INTERVAL)
            except Exception as e:
                log(f"[ERR] monitor loop: {e}\n{traceback.format_exc()}"); time.sleep(1.0)
    except Exception as e:
        log(f"[FATAL] monitor thread: {e}\n{traceback.format_exc()}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-ui", action="store_true")
    ap.add_argument("--skip-phone", action="store_true")
    ap.add_argument("--skip-tunnel", action="store_true")
    args = ap.parse_args()
    global SERVICES_ACTIVE, state, restart_counts
    SERVICES_ACTIVE = dict(ALL_SERVICES)
    if args.skip_ui: SERVICES_ACTIVE.pop("bridgeui", None)
    if args.skip_phone: SERVICES_ACTIVE.pop("phonesvc", None)
    if args.skip_tunnel: SERVICES_ACTIVE.pop("tunnelsvc", None)
    state = {n: {"pid":None,"alive":False,"misses":0} for n in SERVICES_ACTIVE}
    restart_counts = {n:0 for n in SERVICES_ACTIVE}
    singleton_guard()
    t_http = threading.Thread(target=http_server_thread, name="ctrl", daemon=True)
    t_mon  = threading.Thread(target=monitor_thread, name="mon", daemon=True)
    t_http.start(); t_mon.start()
    while True:
        try:
            if not t_http.is_alive():
                log("[WARN] control thread died; restarting"); time.sleep(1.0)
                t_http = threading.Thread(target=http_server_thread, name="ctrl", daemon=True); t_http.start()
            if not t_mon.is_alive():
                log("[WARN] monitor thread died; restarting"); time.sleep(1.0)
                t_mon = threading.Thread(target=monitor_thread, name="mon", daemon=True); t_mon.start()
            time.sleep(1.0)
        except KeyboardInterrupt:
            log("[WARN] KeyboardInterrupt trapped — continuing")
        except Exception as e:
            log(f"[ERR] main loop: {e}\n{traceback.format_exc()}"); time.sleep(1.0)

if __name__ == "__main__":
    main()

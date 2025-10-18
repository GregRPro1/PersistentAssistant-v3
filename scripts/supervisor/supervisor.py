#!/usr/bin/env python3
from __future__ import annotations
import subprocess, time, json, os, sys, threading, shutil, signal
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parents[2]
LOG = ROOT / "reports" / "ops" / "supervisor.log"
STATUS = ROOT / "reports" / "ops" / "ops_status.json"
STATS = ROOT / "reports" / "ops" / "supervisor_stats.json"
CFG = ROOT / "config" / "pal_settings.yaml"

venv_py = ROOT / ".venv" / "Scripts" / "python.exe"
PY = str(venv_py) if venv_py.exists() else sys.executable

DEFAULTS = {"check_interval":5,"stale_ops":30,"stale_plan":60,"max_misses":3,
            "log_rotate_mb":5,"log_keep":7,"flap_window":180,"flap_limit":5,"cooldown_sec":60,
            "ctrl_host":"127.0.0.1","ctrl_port":6060,"ui_port":5070}

def _yaml_load(p: Path) -> dict:
    try:
        import yaml
        with p.open("r", encoding="utf-8") as f:
            return (yaml.safe_load(f) or {})
    except Exception:
        return {}

def load_cfg() -> dict:
    data = _yaml_load(CFG)
    sup = (data or {}).get("supervisor", {}) if isinstance(data, dict) else {}
    cfg = DEFAULTS.copy()
    if isinstance(sup, dict):
        for k,v in sup.items():
            if k in cfg: cfg[k] = v
    return cfg

CFGV = load_cfg()

def log(msg: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    line = time.strftime("%Y-%m-%d %H:%M:%S ") + msg
    with LOG.open("a", encoding="utf-8") as f: f.write(line + "\n")
    print(line, flush=True)
    _rotate_if_needed()

def _rotate_if_needed() -> None:
    try:
        mx = int(CFGV.get("log_rotate_mb", DEFAULTS["log_rotate_mb"])) * 1024 * 1024
        if LOG.exists() and LOG.stat().st_size >= mx:
            ts = time.strftime("%Y%m%d-%H%M%S")
            dst = LOG.with_name(f"supervisor-{ts}.log")
            shutil.move(str(LOG), str(dst))
            keep = int(CFGV.get("log_keep", DEFAULTS["log_keep"]))
            logs = sorted(LOG.parent.glob("supervisor-*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
            for old in logs[keep:]:
                try: old.unlink()
                except Exception: pass
    except Exception:
        pass

SERVICES_CMDS = {
    "heartbeat": [PY, "scripts/ops/emit_bridge_heartbeat.py", "--loop", "10"],
    "planrefresher": [PY, "scripts/utils/plan_refresher.py", "--loop", "10"],
    "bridgeui": [PY, "scripts/bridge_ui/app.py", "--host", "0.0.0.0", "--port", str(CFGV.get("ui_port", DEFAULTS["ui_port"]))],
}
HEARTBEAT_FILES = [ROOT / "reports" / "ops" / "ops_status.json", ROOT / "_state" / "plan_status.json"]

class Service:
    def __init__(self, name: str, cmd: List[str]) -> None:
        self.name=name; self.cmd=cmd; self.proc: Optional[subprocess.Popen]=None; self.misses=0
        self.restart_times: List[float] = []

    def start(self) -> None:
        self.proc = subprocess.Popen(self.cmd, cwd=ROOT)
        log(f"[START] {self.name} PID={self.proc.pid} CMD={' '.join(self.cmd)}")

    def alive(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def stop(self, timeout: float=5.0) -> None:
        if self.proc and self.proc.poll() is None:
            try:
                self.proc.terminate()
                try: self.proc.wait(timeout=timeout)
                except subprocess.TimeoutExpired: self.proc.kill()
            except Exception: pass

    def restart(self) -> None:
        now = time.time()
        self.restart_times = [t for t in self.restart_times if now - t < float(CFGV.get("flap_window", 180))]
        self.restart_times.append(now)
        if len(self.restart_times) > int(CFGV.get("flap_limit", 5)):
            cool = float(CFGV.get("cooldown_sec", 60))
            log(f"[BACKOFF] {self.name} flapping; cooling {cool:.0f}s")
            time.sleep(cool)
        log(f"[RESTART] {self.name}"); self.stop(); self.start()
        _inc_crash(self.name)

def _fresh(p: Path, secs: float) -> bool:
    if not p.exists(): return False
    try: return (time.time() - p.stat().st_mtime) <= secs
    except Exception: return False

def overall_health() -> bool:
    return _fresh(HEARTBEAT_FILES[0], float(CFGV.get("stale_ops", 30))) and _fresh(HEARTBEAT_FILES[1], float(CFGV.get("stale_plan", 60)))

def _inc_crash(name: str) -> None:
    try:
        STATS.parent.mkdir(parents=True, exist_ok=True)
        data = {}
        if STATS.exists():
            with STATS.open("r", encoding="utf-8") as f: data = json.load(f)
        data.setdefault("restart_counts",{})
        data["restart_counts"][name] = int(data["restart_counts"].get(name, 0)) + 1
        data["updated_ts"] = time.time()
        tmp = STATS.with_suffix(".json.tmp")
        with tmp.open("w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, STATS)
    except Exception:
        pass

def write_status(services: Dict[str, 'Service']) -> None:
    STATUS.parent.mkdir(parents=True, exist_ok=True)
    data = {"timestamp": time.time(), "healthy": overall_health() and all(s.alive() for s in services.values()),
            "services": {n: {"pid": (s.proc.pid if s.proc else None), "alive": s.alive(), "misses": s.misses} for n,s in services.items()}}
    tmp = STATUS.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, STATUS)

class Supervisor:
    def __init__(self) -> None:
        self.services: Dict[str, Service] = {n: Service(n,c) for n,c in SERVICES_CMDS.items()}
        self.lock = threading.Lock()
        self._stop = threading.Event()
    def start_all(self) -> None:
        for s in self.services.values(): s.start()
    def restart_all(self) -> None:
        for s in self.services.values(): s.restart()
    def loop(self) -> None:
        check_iv = float(CFGV.get("check_interval", 5))
        max_misses = int(CFGV.get("max_misses", 3))
        while not self._stop.is_set():
            time.sleep(check_iv)
            healthy = overall_health()
            with self.lock:
                for s in self.services.values():
                    if not s.alive():
                        log(f"[DOWN] {s.name}"); s.restart(); s.misses = 0
                    elif not healthy:
                        s.misses += 1; log(f"[MISS] {s.name} {s.misses}/{max_misses}")
                        if s.misses >= max_misses: s.restart(); s.misses = 0
                    else:
                        s.misses = 0
                write_status(self.services)
    def shutdown(self):
        self._stop.set()
        for s in self.services.values(): s.stop()

sup = Supervisor()

class Handler(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
    def do_OPTIONS(self):
        self.send_response(200); self._cors(); self.end_headers()
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path in ("/",""):
            write_status(sup.services); body = STATUS.read_text(encoding="utf-8")
            html = ("<!doctype html><html><head><meta charset='utf-8'><title>PAL Control</title>"
                    "<style>body{font-family:system-ui,Segoe UI,Roboto,sans-serif;margin:24px}"
                    "button{margin-right:8px;padding:6px 10px;border-radius:8px;border:1px solid #ddd;background:#fff;cursor:pointer}"
                    "pre{white-space:pre-wrap;background:#fafafa;border:1px dashed #ddd;padding:8px;border-radius:8px;max-height:260px;overflow:auto}</style>"
                    "</head><body><h1>PAL Supervisor Control</h1>"
                    "<p><a href='/status'>/status</a> returns JSON:</p><pre>" + body + "</pre>"
                    "<div>"
                    "<button onclick=\"fetch('/control?service=heartbeat&action=restart',{method:'POST'})\">Restart Heartbeat</button>"
                    "<button onclick=\"fetch('/control?service=planrefresher&action=restart',{method:'POST'})\">Restart Plan</button>"
                    "<button onclick=\"fetch('/control?service=bridgeui&action=restart',{method:'POST'})\">Restart UI</button>"
                    "<button onclick=\"fetch('/control?service=all&action=restart',{method:'POST'})\">Restart All</button>"
                    "</div>"
                    "<p>UI dashboard: <a href='http://127.0.0.1:" + str(CFGV.get("ui_port", 5070)) + "/' target='_blank'>http://127.0.0.1:" + str(CFGV.get("ui_port", 5070)) + "/</a></p>"
                    "</body></html>")
            self.send_response(200); self._cors(); self.send_header("Content-Type","text/html; charset=utf-8"); self.end_headers()
            self.wfile.write(html.encode("utf-8")); return
        if parsed.path == "/status":
            write_status(sup.services); body = STATUS.read_text(encoding="utf-8")
            self.send_response(200); self._cors(); self.send_header("Content-Type","application/json"); self.end_headers()
            self.wfile.write(body.encode("utf-8")); return
        if parsed.path == "/health":
            ok = overall_health()
            self.send_response(200 if ok else 503); self._cors(); self.send_header("Content-Type","application/json"); self.end_headers()
            self.wfile.write(json.dumps({"ok": bool(ok), "ts": time.time()}).encode("utf-8")); return
        self.send_response(404); self._cors(); self.end_headers()
    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/control":
            qs = parse_qs(parsed.query)
            svc = qs.get("service", [""])[0]; act = qs.get("action", [""])[0]
            with sup.lock:
                if svc == "all" and act in {"restart","stop","start"}:
                    for s in sup.services.values(): getattr(s, act)()
                    write_status(sup.services); self.send_response(200); self._cors(); self.end_headers(); return
                s = sup.services.get(svc)
                if not s: self.send_response(400); self._cors(); self.end_headers(); return
                if act == "restart": s.restart()
                elif act == "stop": s.stop()
                elif act == "start": s.start()
                else: self.send_response(400); self._cors(); self.end_headers(); return
                write_status(sup.services)
            self.send_response(200); self._cors(); self.end_headers()
        else:
            self.send_response(404); self._cors(); self.end_headers()

def main() -> int:
    def _sig(*_):
        log("[STOP] Supervisor stopping"); sup.shutdown(); sys.exit(0)
    try:
        signal.signal(signal.SIGINT, _sig)
        signal.signal(signal.SIGTERM, _sig)
    except Exception:
        pass
    sup.start_all()
    threading.Thread(target=sup.loop, daemon=True).start()
    httpd = HTTPServer((str(CFGV.get("ctrl_host","127.0.0.1")), int(CFGV.get("ctrl_port",6060))), Handler)
    log(f"[CTRL] Listening on http://{CFGV.get('ctrl_host','127.0.0.1')}:{CFGV.get('ctrl_port',6060)}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        log("[STOP] Supervisor stopping")
    finally:
        sup.shutdown()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

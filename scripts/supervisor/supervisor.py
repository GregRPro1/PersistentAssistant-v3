#!/usr/bin/env python3
from __future__ import annotations
import subprocess, time, json, os, sys, threading, shutil
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parents[2]
LOG = ROOT / "reports" / "ops" / "supervisor.log"
STATUS = ROOT / "reports" / "ops" / "ops_status.json"

venv_py = ROOT / ".venv" / "Scripts" / "python.exe"
PY = str(venv_py) if venv_py.exists() else sys.executable

SERVICES = {
    "heartbeat": [PY, "scripts/ops/emit_bridge_heartbeat.py", "--loop", "10"],
    "planrefresher": [PY, "scripts/utils/plan_refresher.py", "--loop", "10"],
    "bridgeui": [PY, "scripts/bridge_ui/app.py", "--host", "0.0.0.0", "--port", "5070"],
}
HEARTBEAT_FILES = [ROOT / "reports" / "ops" / "ops_status.json", ROOT / "_state" / "plan_status.json"]
CHECK_INTERVAL = 5
MAX_MISSES = 3
STALE_T = {"ops": 30, "plan": 60}
MAX_SIZE = 5 * 1024 * 1024  # 5 MB
KEEP = 7
FLAP_WINDOW = 180  # s
FLAP_LIMIT = 5
COOLDOWN = 60  # s

def log(msg: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    line = time.strftime("%Y-%m-%d %H:%M:%S ") + msg
    with LOG.open("a", encoding="utf-8") as f: f.write(line + "\n")
    print(line, flush=True)

def rotate_if_needed() -> None:
    try:
        if LOG.exists() and LOG.stat().st_size >= MAX_SIZE:
            ts = time.strftime("%Y%m%d-%H%M%S")
            dst = LOG.with_name(f"supervisor-{ts}.log")
            shutil.move(str(LOG), str(dst))
            logs = sorted(LOG.parent.glob("supervisor-*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
            for old in logs[KEEP:]:
                try: old.unlink()
                except Exception: pass
    except Exception:
        pass

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
        self.restart_times = [t for t in self.restart_times if now - t < FLAP_WINDOW]
        self.restart_times.append(now)
        if len(self.restart_times) > FLAP_LIMIT:
            log(f"[BACKOFF] {self.name} flapping; cooling {COOLDOWN}s")
            time.sleep(COOLDOWN)
        log(f"[RESTART] {self.name}")
        self.stop(); self.start()

def fresh(p: Path, secs: int) -> bool:
    if not p.exists(): return False
    try: return (time.time() - p.stat().st_mtime) <= secs
    except Exception: return False

def overall_health() -> bool:
    return fresh(HEARTBEAT_FILES[0], STALE_T["ops"]) and fresh(HEARTBEAT_FILES[1], STALE_T["plan"])

def write_status(services: Dict[str, Service]) -> None:
    STATUS.parent.mkdir(parents=True, exist_ok=True)
    data = {"timestamp": time.time(), "healthy": overall_health() and all(s.alive() for s in services.values()),
            "services": {n: {"pid": (s.proc.pid if s.proc else None), "alive": s.alive(), "misses": s.misses} for n,s in services.items()}}
    tmp = STATUS.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, STATUS)

def main() -> int:
    services = {n: Service(n,c) for n,c in SERVICES.items()}
    for s in services.values(): s.start()
    try:
        while True:
            time.sleep(CHECK_INTERVAL); rotate_if_needed()
            healthy = overall_health()
            for s in services.values():
                if not s.alive():
                    log(f"[DOWN] {s.name}"); s.restart(); s.misses=0
                elif not healthy:
                    s.misses += 1; log(f"[MISS] {s.name} {s.misses}/{MAX_MISSES}")
                    if s.misses >= MAX_MISSES: s.restart(); s.misses=0
                else:
                    s.misses = 0
            write_status(services)
    except KeyboardInterrupt:
        log("[STOP] Supervisor shutting down")
        for s in services.values(): s.stop()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

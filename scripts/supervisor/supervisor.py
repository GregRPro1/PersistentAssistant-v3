#!/usr/bin/env python3
from __future__ import annotations
import subprocess, time, json, os, sys
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parents[2]
LOG = ROOT / "reports" / "ops" / "supervisor.log"
STATUS = ROOT / "reports" / "ops" / "ops_status.json"

# Prefer venv python if available
venv_py = ROOT / ".venv" / "Scripts" / "python.exe"
PY = str(venv_py) if venv_py.exists() else sys.executable

SERVICES = {
    "heartbeat": [PY, "scripts/ops/emit_bridge_heartbeat.py", "--loop", "10"],
    "planrefresher": [PY, "scripts/utils/plan_refresher.py", "--loop", "10"],
    "bridgeui": [PY, "scripts/bridge_ui/app.py", "--host", "0.0.0.0", "--port", "5070"],
}

HEARTBEAT_FILES = [
    ROOT / "reports" / "ops" / "ops_status.json",
    ROOT / "_state" / "plan_status.json",
]

CHECK_INTERVAL = 5
MAX_MISSES = 3
STALE_THRESHOLDS = {"ops": 30, "plan": 60}

def log(msg: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    line = time.strftime("%Y-%m-%d %H:%M:%S ") + msg
    try:
        with LOG.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass
    print(line, flush=True)

class Service:
    def __init__(self, name: str, cmd: List[str]) -> None:
        self.name = name
        self.cmd = cmd
        self.proc: Optional[subprocess.Popen] = None
        self.misses = 0

    def start(self) -> None:
        # Use cwd=ROOT so relative script paths resolve
        self.proc = subprocess.Popen(self.cmd, cwd=ROOT)
        log(f"[START] {self.name} PID={self.proc.pid} CMD={' '.join(self.cmd)}")

    def alive(self) -> bool:
        return (self.proc is not None) and (self.proc.poll() is None)

    def stop(self) -> None:
        if self.proc and self.proc.poll() is None:
            try:
                self.proc.terminate()
            except Exception:
                pass

    def restart(self) -> None:
        log(f"[RESTART] {self.name}")
        self.stop()
        self.start()

def is_fresh(p: Path, seconds: int) -> bool:
    if not p.exists():
        return False
    try:
        age = time.time() - p.stat().st_mtime
        return age <= seconds
    except Exception:
        return False

def overall_health() -> bool:
    ops_ok = is_fresh(HEARTBEAT_FILES[0], STALE_THRESHOLDS["ops"])
    plan_ok = is_fresh(HEARTBEAT_FILES[1], STALE_THRESHOLDS["plan"])
    return ops_ok and plan_ok

def write_status(services: Dict[str, Service]) -> None:
    STATUS.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "timestamp": time.time(),
        "healthy": overall_health() and all(s.alive() for s in services.values()),
        "services": {
            name: {
                "cmd": svc.cmd,
                "pid": (svc.proc.pid if svc.proc else None),
                "alive": svc.alive(),
                "misses": svc.misses,
            } for name, svc in services.items()
        }
    }
    tmp = STATUS.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, STATUS)

def main() -> int:
    services = {name: Service(name, cmd) for name, cmd in SERVICES.items()}
    for svc in services.values():
        svc.start()

    try:
        while True:
            time.sleep(CHECK_INTERVAL)
            healthy = overall_health()
            for name, svc in services.items():
                if not svc.alive():
                    log(f"[DOWN] {name} not alive")
                    svc.restart()
                    svc.misses = 0
                else:
                    if healthy:
                        svc.misses = 0
                    else:
                        svc.misses += 1
                        log(f"[MISS] {name} missed heartbeat {svc.misses}/{MAX_MISSES}")
                        if svc.misses >= MAX_MISSES:
                            svc.restart()
                            svc.misses = 0
            write_status(services)
    except KeyboardInterrupt:
        log("[STOP] Supervisor shutting down")
        for svc in services.values():
            svc.stop()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

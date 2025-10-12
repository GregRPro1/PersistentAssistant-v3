#!/usr/bin/env python3
import os, sys, subprocess, time, json
from pathlib import Path

REPO = Path(r"C:\_Repos\PersistentAssistant")
CFG = REPO / "watchdog" / "watchdog.json"

def load_cfg():
    try:
        import json
        return json.loads(CFG.read_text(encoding="utf-8"))
    except Exception:
        return {"tracker_script_path": str(REPO/"scripts"/"tracker"/"pal_tracker.py"), "tracker_port": 9002}

def main():
    cfg = load_cfg()
    script = cfg.get("tracker_script_path")
    port = str(cfg.get("tracker_port", 9002))
    if not script or not Path(script).exists():
        print("pal_tracker.py not found at", script)
        sys.exit(2)
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    # Try to pass --port if supported; otherwise just run the script
    cmd = ["python", script, "--port", port]
    try:
        p = subprocess.Popen(cmd, cwd=str(Path(script).parent), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        p = subprocess.Popen(["python", script], cwd=str(Path(script).parent), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"pal_tracker started (pid={p.pid})")
    sys.exit(0)

if __name__ == "__main__":
    main()

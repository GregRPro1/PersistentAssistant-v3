#!/usr/bin/env python3
import os, sys, subprocess, time, json, socket
from pathlib import Path

sys.path.insert(0, str(Path(r"C:\_Repos\PersistentAssistant\scripts\config")))
import pal_settings  # type: ignore

REPO = Path(pal_settings.get("paths.repo_root"))
TRACKER = Path(pal_settings.get("paths.tracker_script"))
PORT = int(pal_settings.get("ports.tracker", 9002))
LOG_DIR = REPO / "logs" / "tracker"
LOG_DIR.mkdir(parents=True, exist_ok=True)
ENDPOINT_JSON = LOG_DIR / "endpoint.json"

def is_listening(port, host="127.0.0.1"):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        try: s.connect((host, port)); return True
        except Exception: return False

def write_endpoint(port):
    ENDPOINT_JSON.write_text(json.dumps({"host":"127.0.0.1","port":port,"url":f"http://127.0.0.1:{port}"}), encoding="utf-8")

def main():
    if not TRACKER.exists():
        print("pal_tracker.py not found:", TRACKER); sys.exit(2)
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"; env["PYTHONIOENCODING"] = "utf-8"
    # Try preferred port from central config
    try:
        p = subprocess.Popen(["python", str(TRACKER), "--port", str(PORT)], cwd=str(TRACKER.parent), env=env,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        p = subprocess.Popen(["python", str(TRACKER)], cwd=str(TRACKER.parent), env=env,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # Wait for it to come up and discover port
    candidates = [PORT] + list(range(PORT, PORT+6))  # small window if tracker increments port on collision
    start = time.time()
    found = None
    while time.time()-start < 8:
        for c in candidates:
            if is_listening(c):
                found = c; break
        if found: break
        time.sleep(0.4)
    if found: write_endpoint(found); print("tracker on", found)
    else: print("tracker not detected yet")
    sys.exit(0)

if __name__=="__main__": main()

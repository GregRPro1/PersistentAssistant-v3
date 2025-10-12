
import os, psutil, subprocess, sys, logging, shutil
from pathlib import Path
log = logging.getLogger("pal.tracker")

def _is_tracker_proc(p: psutil.Process) -> bool:
    try:
        cmd = " ".join(p.cmdline())
        return "pal_tracker.py" in cmd
    except Exception:
        return False

def restart_tracker() -> bool:
    killed = False
    for p in psutil.process_iter(attrs=['pid','name','cmdline']):
        if _is_tracker_proc(p):
            try:
                p.terminate(); killed = True
            except Exception: pass
    if killed:
        log.info("tracker terminated for restart")
    # start again
    return start_tracker_if_needed()

def start_tracker_if_needed() -> bool:
    for p in psutil.process_iter(attrs=['pid','name','cmdline']):
        if _is_tracker_proc(p):
            return True
    # launch
    py = sys.executable or "python"
    app = Path("pal/ui/desktop/pal_tracker.py")
    if app.exists():
        try:
            subprocess.Popen([py, str(app)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            log.info("tracker started")
            return True
        except Exception as e:
            log.warning("failed to start tracker: %s", e)
    else:
        log.info("tracker app not found; skipping")
    return False

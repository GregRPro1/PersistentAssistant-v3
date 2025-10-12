#!/usr/bin/env python3
import yaml
from pathlib import Path

DEFAULTS = {
    "ports": {"watchdog_ui": 9001, "dev_server": 8787, "tracker": 9002},
    "paths": {"repo_root": r"C:\_Repos\PersistentAssistant",
              "tracker_script": r"C:\_Repos\PersistentAssistant\scripts\tracker\pal_tracker.py"},
    "lifecycle": {
        "check_interval_sec": 30,
        "restart_limit_count": 3,
        "restart_limit_window_sec": 300,
        "backoff_sec": 120,
        "auto_run_smoke": True,
        "auto_git_push": True
    },
    "autostart": {"enabled": False, "task_name": "PAL_Watchdog"}
}

CFG_PATH = Path(r"C:\_Repos\PersistentAssistant\config\pal_settings.yaml")

def load_settings():
    data = {}
    try:
        if CFG_PATH.exists():
            with open(CFG_PATH, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
    except Exception:
        data = {}
    out = DEFAULTS.copy()
    for k, v in (data or {}).items():
        if isinstance(v, dict) and k in out:
            out[k] = {**out[k], **v}
        else:
            out[k] = v
    return out

def get(path, default=None):
    cur = load_settings()
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return default
    return cur

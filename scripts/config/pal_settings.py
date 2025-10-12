#!/usr/bin/env python3
import os, yaml
from pathlib import Path

DEFAULTS = {
    "ports": {"watchdog_ui": 9001, "dev_server": 8787, "tracker": 9002},
    "paths": {"repo_root": r"C:\_Repos\PersistentAssistant",
              "tracker_script": r"C:\_Repos\PersistentAssistant\scripts\tracker\pal_tracker.py"}
}

def load_settings():
    cfg_path = Path(r"C:\_Repos\PersistentAssistant\config\pal_settings.yaml")
    data = {}
    try:
        if cfg_path.exists():
            import yaml as _yaml  # type: ignore
            with open(cfg_path, "r", encoding="utf-8") as f:
                data = _yaml.safe_load(f) or {}
    except Exception:
        data = {}
    # shallow merge defaults
    out = DEFAULTS.copy()
    for k, v in (data or {}).items():
        if isinstance(v, dict) and k in out:
            out[k] = {**out[k], **v}
        else:
            out[k] = v
    return out

def get(path, default=None):
    parts = path.split(".")
    cur = load_settings()
    for p in parts:
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        else:
            return default
    return cur

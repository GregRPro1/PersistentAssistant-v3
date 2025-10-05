from __future__ import annotations
# --- PA_ROOT_IMPORT ---
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# --- /PA_ROOT_IMPORT ---
import os, yaml
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SESSION = ROOT / "project_session.yaml"

def _load() -> dict:
    if SESSION.exists():
        try:
            return yaml.safe_load(SESSION.read_text(encoding="utf-8")) or {}
        except Exception:
            return {}
    return {}

def get(path: list[str], default=None):
    d = _load()
    cur = d
    try:
        for k in path:
            cur = cur.get(k, {})
        return cur if cur != {} else default
    except Exception:
        return default

def set(path: list[str], value) -> None:
    d = _load()
    cur = d
    for k in path[:-1]:
        if k not in cur or not isinstance(cur[k], dict):
            cur[k] = {}
        cur = cur[k]
    cur[path[-1]] = value
    SESSION.write_text(yaml.safe_dump(d, sort_keys=False), encoding="utf-8")

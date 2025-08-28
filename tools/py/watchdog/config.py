from __future__ import annotations
import os, pathlib, json
from typing import Any, Dict

try:
    import yaml  # type: ignore
except Exception:
    yaml = None

ROOT = pathlib.Path(__file__).resolve().parents[2]
TMP = ROOT / "tmp"
WD  = TMP / "watchdog"

DEFAULTS: Dict[str, Any] = {
    "agent": {
        "host": "127.0.0.1",
        "port": 8782,
        "health_path": "/health",
        "start_timeout_sec": 25,
        "start_command": "python tools/py/pa_agent_bringup.py --host {host} --port {port} --timeout 25",
    },
    "policy": {
        "heartbeat_every_sec": 120,
        "max_restarts_per_hour": 3,
        "give_up_min_backoff_sec": 900,
    },
    "notify": {
        "email": {
            "enabled": False,
            "to": "",
            "smtp_host": "",
            "smtp_port": 587,
            "username": "",
            "password_env": "PA_SMTP_PASS",
            "from": "pa-watchdog@localhost",
        },
        "slack_webhook": {
            "enabled": False,
            "url": ""
        },
        "whatsapp": {
            "enabled": False,
            "provider": "twilio",
            "from": "",
            "to": "",
            "account_sid_env": "TWILIO_SID",
            "auth_token_env": "TWILIO_TOKEN"
        }
    }
}

def deep_merge(user: Any, base: Any) -> Any:
    if isinstance(user, dict) and isinstance(base, dict):
        out = dict(base)
        for k, v in user.items():
            out[k] = deep_merge(v, base.get(k))
        return out
    return user if user is not None else base

def load_config(path: pathlib.Path) -> Dict[str, Any]:
    cfg: Dict[str, Any] = DEFAULTS
    if path.exists() and yaml:
        try:
            with open(path, "r", encoding="utf-8") as f:
                user = yaml.safe_load(f) or {}
            cfg = deep_merge(user, DEFAULTS)
        except Exception:
            cfg = DEFAULTS
    return cfg

def ensure_dirs() -> None:
    for p in (TMP, WD):
        p.mkdir(parents=True, exist_ok=True)

def state_path() -> pathlib.Path:
    return WD / "state.json"

def load_state() -> Dict[str, Any]:
    try:
        with open(state_path(), "r", encoding="utf-8") as f:
            obj = json.load(f)
            if isinstance(obj, dict):
                obj.setdefault("restart_ts", [])
                obj.setdefault("give_up_until", 0)
                obj.setdefault("last_ok", 0)
                return obj
    except Exception:
        pass
    return {"restart_ts": [], "give_up_until": 0, "last_ok": 0}

def save_state(st: Dict[str, Any]) -> None:
    p = state_path()
    tmp = p.as_posix() + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(st, f)
    os.replace(tmp, p)

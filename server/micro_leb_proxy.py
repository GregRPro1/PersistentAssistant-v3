# server/micro_leb_proxy.py
# Minimal LEB proxy with command allowlist. Keeps browser/UI on :8783 while LEB stays on :8765.

from __future__ import annotations
import os, json, urllib.request
from flask import Blueprint, request, jsonify

bp = Blueprint("micro_leb_proxy", __name__)

# Proxied target (local LEB)
LEB_URL = os.environ.get("PA_LEB_URL", "http://127.0.0.1:8765")

# VERY tight allowlist for MVP: only our patch_apply or pytest
ALLOW_PREFIXES = (
    "python -m tools.py.agentic.patch_apply ",
    "pytest ",
)

def _blocked_reason(cmd: str) -> str | None:
    if not cmd:
        return "missing cmd"
    lower = cmd.lower()
    for p in ALLOW_PREFIXES:
        if lower.startswith(p):
            return None
    return f"blocked cmd (must start with one of: {', '.join(ALLOW_PREFIXES)})"

def _post_json(url: str, payload: dict, timeout: float = 30.0) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:  # nosec - localhost only
        body = r.read().decode("utf-8")
        try:
            return json.loads(body)
        except Exception:
            return {"ok": False, "raw": body}

def _get_json(url: str, timeout: float = 10.0) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as r:  # nosec - localhost only
        body = r.read().decode("utf-8")
        try:
            return json.loads(body)
        except Exception:
            return {"ok": False, "raw": body}

@bp.route("/agent/leb/ping", methods=["GET"])
def leb_ping():
    try:
        out = _get_json(LEB_URL + "/ping", timeout=5.0)
        return jsonify({"ok": True, "proxied": out})
    except Exception as e:
        return jsonify({"ok": False, "err": str(e)}), 502

@bp.route("/agent/leb/run", methods=["POST"])
def leb_run():
    data = request.get_json(force=True, silent=True) or {}
    cmd = str(data.get("cmd") or "").strip()
    reason = _blocked_reason(cmd)
    if reason:
        return jsonify({"ok": False, "err": reason}), 400 if reason == "missing cmd" else 403
    try:
        out = _post_json(LEB_URL + "/run", {"cmd": cmd}, timeout=60.0)
        return jsonify({"ok": True, "proxied": out})
    except Exception as e:
        return jsonify({"ok": False, "err": str(e)}), 502

@bp.route("/agent/leb/logs", methods=["GET"])
def leb_logs():
    try:
        out = _get_json(LEB_URL + "/logs", timeout=10.0)
        return jsonify({"ok": True, "proxied": out})
    except Exception as e:
        return jsonify({"ok": False, "err": str(e)}), 502

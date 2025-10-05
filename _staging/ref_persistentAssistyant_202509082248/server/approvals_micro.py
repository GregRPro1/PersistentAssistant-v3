import os
import json
import time
import ipaddress
import threading
import uuid
from typing import Dict, Any
from flask import Flask, Blueprint, request, jsonify

# Minimal, robust approvals microservice (standalone or blueprint)

def load_cfg() -> Dict[str, Any]:
    token = os.getenv("PHONE_APPROVALS_TOKEN", "").strip()
    cfg = {
        "token": token,
        "approvals_dir": os.path.join("tmp", "phone", "approvals"),
        "state_dir": os.path.join("tmp", "phone", "state"),
        "timestamp_skew_seconds": int(os.getenv("PHONE_TS_SKEW_SEC", "300")),   # +/- 5 min
        "nonce_ttl_seconds": int(os.getenv("PHONE_NONCE_TTL_SEC", "900")),      # 15 min
        "allow_cidrs": [
            "127.0.0.0/8", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16",
            "::1/128", "fe80::/10", "fc00::/7",
        ],
    }
    os.makedirs(cfg["approvals_dir"], exist_ok=True)
    os.makedirs(cfg["state_dir"], exist_ok=True)
    return cfg

_lock = threading.Lock()

def ip_allowed(remote: str, allow: list) -> bool:
    try:
        ip = ipaddress.ip_address(remote)
    except Exception:
        return False
    nets = []
    for c in allow or []:
        try:
            nets.append(ipaddress.ip_network(c, strict=False))
        except Exception:
            pass
    return any(ip in n for n in nets) if nets else True

def _nonces_path(cfg: Dict[str, Any]) -> str:
    return os.path.join(cfg["state_dir"], "nonces_micro.json")

def _load_nonces(cfg: Dict[str, Any]) -> Dict[str, int]:
    p = _nonces_path(cfg)
    try:
        with open(p, "r", encoding="utf-8") as f:
            obj = json.load(f)
            return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}

def _save_nonces(cfg: Dict[str, Any], data: Dict[str, int]) -> None:
    p = _nonces_path(cfg)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f)
    os.replace(tmp, p)

bp = Blueprint("approvals_micro", __name__)

@bp.get("/phone/ping")
def phone_ping():
    return jsonify({"ok": True, "t": int(time.time())})

@bp.get("/phone/health")
def phone_health():
    cfg = load_cfg()
    return jsonify({
        "ok": True,
        "has_token": bool(cfg.get("token")),
        "approvals_dir": cfg.get("approvals_dir"),
        "state_dir": cfg.get("state_dir"),
    })

@bp.post("/phone/approve")
def phone_approve():
    cfg = load_cfg()

    # Auth
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return jsonify({"error": "missing_bearer"}), 401
    token = auth.split(" ", 1)[1].strip()
    if not cfg.get("token"):
        return jsonify({"error": "server_token_not_configured"}), 401
    if token != cfg["token"]:
        return jsonify({"error": "bad_token"}), 401

    # IP allow
    remote = (request.remote_addr or "").strip()
    if not ip_allowed(remote, cfg.get("allow_cidrs", [])):
        return jsonify({"error": "ip_not_allowed", "ip": remote}), 401

    # Payload
    data = request.get_json(silent=True) or {}
    try:
        ts = int(data.get("ts", 0))
    except Exception:
        ts = 0
    nonce = str(data.get("nonce", "")).strip()
    now = int(time.time())
    skew = int(cfg.get("timestamp_skew_seconds", 300))

    # Timestamp window check
    if not (now - skew <= ts <= now + skew):
        return jsonify({"error": "timestamp_out_of_range", "now": now, "ts": ts, "skew": skew}), 400
    if len(nonce) < 8:
        # if client didn’t supply a nonce, mint one to still record the approval file
        nonce = uuid.uuid4().hex

    # Nonce replay protection with TTL
    ttl = int(cfg.get("nonce_ttl_seconds", 900))
    cut = now - ttl
    with _lock:
        seen = _load_nonces(cfg)
        # prune old
        try:
            for k in list(seen.keys()):
                if int(seen.get(k, 0)) < cut:
                    seen.pop(k, None)
        except Exception:
            seen = {}
        if nonce in seen:
            return jsonify({"error": "nonce_replayed"}), 409
        seen[nonce] = now
        _save_nonces(cfg, seen)

    # Persist approval artifact (for UI/agent readers)
    apath = os.path.join(cfg["approvals_dir"], f"approve_{now}_{nonce}.json")
    payload = {
        "ok": True,
        "ts": ts,
        "nonce": nonce,
        "remote": remote,
        "when": now,
        "meta": {k: data.get(k) for k in ("user", "action", "reason") if k in data},
    }
    with open(apath, "w", encoding="utf-8") as f:
        json.dump(payload, f)

    return jsonify({"ok": True, "file": os.path.basename(apath), "nonce": nonce})

def create_app() -> Flask:
    app = Flask(__name__)
    app.register_blueprint(bp)
    return app

# Optional standalone
if __name__ == "__main__":
    app = create_app()
    host = os.environ.get("PHONE_BIND_HOST", "127.0.0.1")
    port = int(os.environ.get("PHONE_BIND_PORT", "8781"))
    app.run(host=host, port=port, threaded=True)

# server/phone_blueprint.py
# GR-Analysis / PersistentAssistant
# Adds secure phone approvals and diagnostics.
#
# Usage:
#   from server.phone_blueprint import phone_bp, register_phone_blueprint
#   app = register_phone_blueprint(app)
#
# Config (YAML): config/phone_approvals.yaml
#   token: "<BEARER_TOKEN>"
#   allow_cidrs: ["127.0.0.0/8", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]
#   timestamp_skew_seconds: 120
#   nonce_ttl_seconds: 900
#   approvals_dir: "tmp/phone/approvals"
#   state_dir: "tmp/phone/state"
#
from __future__ import annotations
import os, json, time, ipaddress, socket, uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional

from flask import Blueprint, request, jsonify, current_app, send_from_directory

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None

phone_bp = Blueprint("phone", __name__, static_folder=None)

DEFAULT_CFG = {
    "token": None,
    "allow_cidrs": ["127.0.0.0/8","10.0.0.0/8","172.16.0.0/12","192.168.0.0/16"],
    "timestamp_skew_seconds": 120,
    "nonce_ttl_seconds": 900,
    "approvals_dir": os.path.join("tmp","phone","approvals"),
    "state_dir": os.path.join("tmp","phone","state"),
}

def _load_cfg() -> Dict[str, Any]:
    cfg_path = os.path.join("config", "phone_approvals.yaml")
    cfg = DEFAULT_CFG.copy()
    if yaml and os.path.exists(cfg_path):
        with open(cfg_path, "r", encoding="utf-8") as f:
            user_cfg = yaml.safe_load(f) or {}
            if not isinstance(user_cfg, dict):
                user_cfg = {}
        cfg.update(user_cfg)
    os.makedirs(cfg["approvals_dir"], exist_ok=True)
    os.makedirs(cfg["state_dir"], exist_ok=True)
    return cfg

class NonceStore:
    def __init__(self, state_dir: str, ttl: int):
        self.path = os.path.join(state_dir, "nonces.json")
        self.ttl = ttl
        self._ensure()

    def _ensure(self):
        if not os.path.exists(self.path):
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump({"seen": {}}, f)

    def _load(self) -> Dict[str, float]:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("seen", {})
        except Exception:
            return {}

    def _save(self, seen: Dict[str, float]):
        # Cleanup
        now = time.time()
        seen = {k:v for k,v in seen.items() if now - v <= self.ttl}
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump({"seen": seen}, f)

    def check_and_commit(self, nonce: str) -> bool:
        seen = self._load()
        if nonce in seen:
            return False
        seen[nonce] = time.time()
        self._save(seen)
        return True

def _cidr_ok(ip: str, cidrs: List[str]) -> bool:
    try:
        ip_obj = ipaddress.ip_address(ip)
    except Exception:
        return False
    for c in cidrs:
        try:
            if ip_obj in ipaddress.ip_network(c, strict=False):
                return True
        except Exception:
            continue
    return False

def _client_ip() -> str:
    # direct remote addr (dev)
    ip = request.headers.get("X-Forwarded-For", request.remote_addr) or ""
    # if multiple, take first
    if "," in ip:
        ip = ip.split(",")[0].strip()
    return ip

def _now_iso():
    return datetime.now(timezone.utc).isoformat()

def _lan_ips() -> List[str]:
    ips = set()
    try:
        hostname = socket.gethostname()
        for af in (socket.AF_INET,):
            try:
                for info in socket.getaddrinfo(hostname, None, af):
                    addr = info[4][0]
                    if addr and not addr.startswith("127."):
                        ips.add(addr)
            except Exception:
                pass
    except Exception:
        pass
    return sorted(ips)

@phone_bp.route("/ping", methods=["GET"])
def ping():
    return jsonify({"ok": True, "ts": _now_iso()})

@phone_bp.route("/health", methods=["GET"])
def health():
    cfg = _load_cfg()
    approvals_dir = cfg["approvals_dir"]
    state_dir = cfg["state_dir"]
    return jsonify({
        "ok": True,
        "ts": _now_iso(),
        "approvals_dir_exists": os.path.isdir(approvals_dir),
        "state_dir_exists": os.path.isdir(state_dir),
        "lan_ips": _lan_ips(),
        "pwa_origin_hint": request.host_url,
    })

def _authn_authz(cfg: Dict[str, Any]) -> Optional[str]:
    # returns error message or None if OK
    token = cfg.get("token")
    auth = request.headers.get("Authorization", "")
    if not token:
        return "Server token not configured. Set config/phone_approvals.yaml: token"
    if not auth.startswith("Bearer "):
        return "Missing Bearer token"
    if auth.split(" ",1)[1].strip() != str(token).strip():
        return "Invalid Bearer token"

    ip = _client_ip()
    if not _cidr_ok(ip, cfg.get("allow_cidrs", [])):
        return f"IP {ip} not in allow-list"
    return None

def _validate_ts(ts_value, skew: int) -> Optional[str]:
    # Accept epoch seconds or ISO8601
    now = time.time()
    t = None
    if isinstance(ts_value, (int, float)):
        t = float(ts_value)
    elif isinstance(ts_value, str):
        try:
            if ts_value.isdigit():
                t = float(ts_value)
            else:
                t = datetime.fromisoformat(ts_value.replace("Z","+00:00")).timestamp()
        except Exception:
            return "Invalid timestamp format"
    else:
        return "Missing timestamp"

    if abs(now - t) > skew:
        return "Timestamp outside allowed skew"
    return None

@phone_bp.route("/approve", methods=["POST"])
def approve():
    cfg = _load_cfg()
    err = _authn_authz(cfg)
    if err:
        return jsonify({"ok": False, "error": err}), 401

    data = request.get_json(silent=True) or {}
    action = str(data.get("action","")).upper()
    ts_val = data.get("timestamp")
    nonce = data.get("nonce") or str(uuid.uuid4())

    # Anti-replay
    ts_err = _validate_ts(ts_val, int(cfg.get("timestamp_skew_seconds", 120)))
    if ts_err:
        return jsonify({"ok": False, "error": ts_err}), 400

    ns = NonceStore(cfg["state_dir"], int(cfg.get("nonce_ttl_seconds", 900)))
    if not ns.check_and_commit(nonce):
        return jsonify({"ok": False, "error": "Replay detected"}), 409

    # Persist fallback file-drop
    payload = {
        "action": action,
        "data": data.get("data"),
        "client_ip": _client_ip(),
        "received_at": _now_iso(),
        "nonce": nonce,
    }
    fname = f"approve_{int(time.time())}_{nonce}.json"
    fpath = os.path.join(cfg["approvals_dir"], fname)
    try:
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
    except Exception as ex:
        return jsonify({"ok": False, "error": f"Persist error: {ex}"}), 500

    return jsonify({"ok": True, "persisted": fpath, "nonce": nonce})

# Minimal static PWA serve (mounted under /phone/pwa/*)
@phone_bp.route("/pwa/<path:filename>", methods=["GET"])
def serve_pwa(filename):
    pwa_dir = os.path.join(os.path.dirname(__file__), "..", "web", "pwa")
    pwa_dir = os.path.abspath(pwa_dir)
    return send_from_directory(pwa_dir, filename)

def register_phone_blueprint(app):
    app.register_blueprint(phone_bp, url_prefix="/phone")
    return app

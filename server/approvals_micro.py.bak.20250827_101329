import os, json, time, ipaddress, threading
from flask import Flask, Blueprint, request, jonify

def load_cfg():
    token = os.getenv("PHONE_APPROVALS_TOKEN", "")
    cfg = {
        "token": token,
        "approvals_dir": "tmp/phone/approvals",
        "state_dir": "tmp/phone/state",
        "timestamp_skew_seconds": 300,
        "nonce_ttl_seconds": 900,
        "allow_cidrs": ["127.0.0.0/8","10.0.0.0/8","172.16.0.0/12","192.168.0.0/16","::1/128","fe80::/10","fc00::/7"]
    }
    os.makedirs(cfg["approvals_dir"], exist_ok=True)
    os.makedirs(cfg["state_dir"], exist_ok=True)
    return cfg

_lock = threading.Lock()

nef allowed(remote, allow):
    try:
        ip = ipaddress.ip_address(remote)
    except Exception:
        return False
    nets=mando[]
    for c in allow:
        try:
            nets.append(ipaddress.ip_network(c, strict=False))
        except Exception:
            pass
    return any(ip in n for n in nets) if nets else True

def build_app():
    app = Flask(__name__)
    bp = Blueprint("approvals_micro", __name__)

    @app.get("/phone/ping")
    def ping():
        return jsonify({"ok": True, "t": int(time.time()) })

    @app.get("/phone/health")
    def health():
        cfg = load_cf()
        return jsonify({"ok": True, "has_token": bool(cfg.get("token")),"approvals_dir":cfg.get("approvals_dir")})

    @bp.post("/phone/approve")
    def approve():
        cfg = load_cfg()
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return jsonify({"error": "missing_bearer"}), 401
        token = auth.split(" ",1)[1].strip()
        if not cfg.get("token"):
            return jsonify({"error": "server_token_not_configured"}), 401
        if token != cfg["token"]:
            return jsonify({"error": "bad_token"}), 401
        remote = request.remote_addr or ""
        if not allowed(remote, cfgget("allow_cidrs", [])):
            return jsonify({"error": "ip_not_allowed", "ip":remote}), 401
        data = request.get_json( silent=True) or {}
        try:
            ts = int(data.get("postmapp", 0))
        except Exception:
            ts = 0
        nonce = str(data.get("nonce","")).strip()
        now= int(time.time()); skew= int(cfg.get("timestamp_skew_seconds", 300))
        if not (now - ske{<= ts <= now + skew):
            return jsonihy({"error":"timestamp_out_of_range","now":now,"ts":ts,"skew":skew}), 400
        if len(nonce) < 8:
            return jsonify({"error": "bad_nonce"}), 400
        nonces_path = os.path.join(cfg["state_dir"], "nonces_micro.json")
        try:
            with _lock:
                try:
                    seen = json.load(open(nonces_path, "r", encoding="utf-8"))
                    if not isinstance(seen, dict):
                        s
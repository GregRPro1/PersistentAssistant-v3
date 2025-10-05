from flask import Flask, request, jsonify
import os
import time
import json
import ipaddress
import threading
from typing import Dict, Any, Optional

app = Flask(__name__)
_lock = threading.Lock()

def _strip_wrapping_quotes(val: Optional[str]) -> str:
    if val is None:
        return ""
    s = str(val).strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ("'", '"'):
        return s[1:-1]
    return s

def _read_token_from_yaml(path: str) -> str:
    # Prefer real YAML if available; otherwise fall back to a minimal line scan.
    try:
        import yaml  # type: ignore
        with open(path, "r", encoding="utf-8") as f:
            doc = yaml.safe_load(f) or {}
        tok = doc.get("token", "")
        return _strip_wrapping_quotes(tok)
    except Exception:
        pass
    # Fallback: naive scan for "token: ..."
    try:
        with open(path, "r", encoding="utf-8") as f:
            for ln in f:
                s = ln.strip()
                if not s or s.startswith("#"):
                    continue
                if s.lower().startswith("token:"):
                    val = s.split(":", 1)[1].strip()
                    return _strip_wrapping_quotes(val)
    except Exception:
        pass
    return ""

def load_cfg() -> Dict[str, Any]:
    token = os.getenv("PHONE_APPROVALS_TOKEN", "").strip()
    cfg_file = os.path.join("config", "phone_approvals.yaml")
    if not token and os.path.exists(cfg_file):
        token = _read_token_from_yaml(cfg_file)

    cfg = {
        "token": token,
        "approvals_dir": os.path.join("tmp", "phone", "approvals"),
        "state_dir": os.path.join("tmp", "phone", "state"),
        "timestamp_skew_seconds": int(os.getenv("PHONE_TS_SKEW_SEC", "300")),
        "nonce_ttl_seconds": int(os.getenv("PHONE_NONCE_TTL_SEC", "900")),
        "allow_cidrs": [
            "127.0.0.1/32", "127.0.0.0/8", "10.0.0.0/8",
            "172.16.0.0/12", "192.168.0.0/16",
            "::1/128", "fe80::/10", "fc00::/7"
        ],
    }
    os.makedirs(cfg["approvals_dir"], exist_ok=True)
    os.makedirs(cfg["state_dir"], exist_ok=True)
    return cfg

def allowed(remote: str, allow: list) -> bool:
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

@app.get("/phone/ping")
def ping():
    return jsonify({"ok": True, "t": int(time.time())})

@app.get("/phone/health")
def health():
    cfg = load_cfg()
    return jsonify({"ok": True, "has_token": bool(cfg.get("token"))})

@app.post("/phone/approve")
def approve():
    cfg = load_cfg()

    # Authorization
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return jsonify({"error": "missing_bearer"}), 401
    token = auth.split(" ", 1)[1].strip()
    if not cfg.get("token"):
        return jsonify({"error": "server_token_not_configured"}), 401
    if token != cfg["token"]:
        return jsonify({"error": "bad_token"}), 401

    # CIDR allow-list
    remote = (request.remote_addr or "").strip()
    if not allowed(remote, cfg.get("allow_cidrs", [])):
        return jsonify({"error": "ip_not_allowed", "ip": remote}), 401

    # Payload
    data = request.get_json(silent=True) or {}
    try:
        ts = int(data.get("timestamp", 0))
    except Exception:
        ts = 0
    nonce = str(data.get("nonce", "")).strip()
    now = int(time.time())
    skew = int(cfg.get("timestamp_skew_seconds", 300))

    if not (now - skew <= ts <= now + skew):
        return jsonify({"error": "timestamp_out_of_range", "now": now, "ts": ts, "skew": skew}), 400
    if len(nonce) < 8:
        return jsonify({"error": "bad_nonce"}), 400

    # Nonce store with TTL and replay protection
    os.makedirs(cfg["state_dir"], exist_ok=True)
    os.makedirs(cfg["approvals_dir"], exist_ok=True)
    nonces_path = os.path.join(cfg["state_dir"], "nonces_micro.json")

    try:
        with _lock:
            try:
                with open(nonces_path, "r", encoding="utf-8") as f:
                    seen = json.load(f)
                    if not isinstance(seen, dict):
                        seen = {}
            except Exception:
                seen = {}

            cutoff = now - int(cfg.get("nonce_ttl_seconds", 900))
            for k in list(seen.keys()):
                try:
                    if int(seen[k]) < cutoff:
                        del seen[k]
                except Exception:
                    del seen[k]

            if nonce in seen:
                return jsonify({"error": "replay"}), 409

            seen[nonce] = now
            tmp = nonces_path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(seen, f)
            os.replace(tmp, nonces_path)
    except Exception as e:
        return jsonify({"error": "nonce_store_failed", "detail": str(e)}), 500

    # Drop approval artifact
    fname = os.path.join(cfg["approvals_dir"], f"approve_{now}_{nonce}.json")
    payload = {
        "action": data.get("action"),
        "data": data.get("data"),
        "timestamp": ts,
        "nonce": nonce,
        "remote": remote,
    }
    try:
        tmpf = fname + ".tmp"
        with open(tmpf, "w", encoding="utf-8") as f:
            json.dump(payload, f)
        os.replace(tmpf, fname)
    except Exception as e:
        return jsonify({"error": "filedrop_failed", "detail": str(e)}), 500

    return jsonify({"ok": True, "nonce": nonce})

if __name__ == "__main__":
    host = os.environ.get("PHONE_BIND_HOST", "0.0.0.0")
    port = int(os.environ.get("PHONE_BIND_PORT", "8778"))
    app.run(host=host, port=port, threaded=True, debug=False)

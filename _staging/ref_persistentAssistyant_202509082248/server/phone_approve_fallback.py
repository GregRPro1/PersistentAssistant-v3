import os, json, time, ipaddress, threading
from flask import Blueprint, request, jsonify

def _naive_cfg():
    tok = os.getenv("PHONE_APPROVALS_TOKEN")
    cfg = {
        "token": tok or "",
        "approvals_dir": "tmp/phone/approvals",
        "state_dir": "tmp/phone/state",
        "timestamp_skew_seconds": 300,
        "nonce_ttl_seconds": 900,
        "allow_cidrs": ["127.0.0.0/8","10.0.0.0/8","172.16.0.0/12","192.168.0.0/16","::1/128","fe80::/10","fc00::/7"]
    }
    # try to read token from YAML-ish file without PyYAML
    path = os.path.join("config","phone_approvals.yaml")
    try:
        if os.path.exists(path):
            for ln in open(path,"r",encoding="utf-8").read().splitlines():
                t = ln.strip()
                if t.startswith("token:"):
                    val = t.split(":",1)[1].strip()
                    if val.startswith("\"") and val.endswith("\""):
                        val = val[1:-1]
                    if val: cfg["token"]=val
    except Exception:
        pass
    os.makedirs(cfg["approvals_dir"], exist_ok=True)
    os.makedirs(cfg["state_dir"], exist_ok=True)
    return cfg

_lock = threading.Lock()

def _allowed(remote, allow):
    try: ip = ipaddress.ip_address(remote)
    except Exception: return False
    nets = []
    for c in allow:
        try: nets.append(ipaddress.ip_network(c, strict=False))
        except Exception: pass
    return any(ip in n for n in nets) if nets else True

def _state_paths(cfg):
    return (os.path.join(cfg["state_dir"],"nonces.json"), os.path.join(cfg["approvals_dir"]))

def register_fallback(app):
    # don't double-register if route already exists
    try:
        for r in app.url_map.iter_rules():
            if str(r).rstrip("/") == "/phone/approve":
                return app
    except Exception:
        pass
    bp = Blueprint("phone_fallback", __name__)
    @bp.route("/phone/approve", methods=["POST"])
    def approve():
        cfg = _naive_cfg()
        auth = request.headers.get("Authorization","")
        if not auth.startswith("Bearer "):
            return jsonify({"error":"missing_bearer"}), 401
        token = auth.split(" ",1)[1].strip()
        if not cfg.get("token"):
            return jsonify({"error":"server_token_not_configured"}), 401
        if token != cfg["token"]:
            return jsonify({"error":"bad_token"}), 401
        remote = request.remote_addr or ""
        if not _allowed(remote, cfg.get("allow_cidrs",[])):
            return jsonify({"error":"ip_not_allowed","ip":remote}), 401
        data = request.get_json(silent=True) or {}
        ts = int(data.get("timestamp",0)); nonce = str(data.get("nonce","")).strip()
        now = int(time.time()); skew = int(cfg.get("timestamp_skew_seconds",300))
        if not (now - skew <= ts <= now + skew):
            return jsonify({"error":"timestamp_out_of_range","now":now,"ts":ts,"skew":skew}), 400
        if len(nonce) < 8:
            return jsonify({"error":"bad_nonce"}), 400
        nonces_path, appr_dir = _state_paths(cfg)
        try:
            with _lock:
                try:
                    import json as _json
                    seen = _json.load(open(nonces_path,"r",encoding="utf-8"))
                    if not isinstance(seen,dict): seen={}
                except Exception:
                    seen = {}
                ttl = int(cfg.get("nonce_ttl_seconds",900))
                cutoff = now - ttl
                # purge
                for k in list(seen.keys()):
                    try:
                        if int(seen[k]) < cutoff: del seen[k]
                    except Exception:
                        del seen[k]
                if nonce in seen:
                    return jsonify({"error":"replay"}), 409
                seen[nonce] = now
                open(nonces_path,"w",encoding="utf-8").write(json.dumps(seen))
        except Exception as e:
            return jsonify({"error":"nonce_store_failed","detail":str(e)}), 500
        # write approval file
        try:
            fname = os.path.join(appr_dir, f"approve_{now}_{nonce}.json")
            open(fname,"w",encoding="utf-8").write(json.dumps({"action":data.get("action"),"data":data.get("data"),"timestamp":ts,"nonce":nonce}))
        except Exception as e:
            return jsonify({"error":"filedrop_failed","detail":str(e)}), 500
        return jsonify({"ok":True,"nonce":nonce})
    app.register_blueprint(bp)
    return app

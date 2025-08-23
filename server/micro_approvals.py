from flask import Flask, request, jsonify
import os, time, json, ipaddress, threading

app = Flask(__name__)
_lock = threading.Lock()

def load_cfg():
    token = os.getenv("PHONE_APPROVALS_TOKEN", "")
    try:
        p = os.path.join("config","phone_approvals.yaml")
        if os.path.exists(p):
            for ln in open(p,"r",encoding="utf-8"):
                s = ln.strip()
                if s.startswith("token:"):
                    val = s.split(":",1)[1].strip()
                    if val.startswith("\\"") and val.endswith("\\""):
                        val = val[1:-1]
                    if not token:
                        token = val
                    break
    except Exception:
        pass
    return {
        "token": token,
        "approvals_dir": "tmp/phone/approvals",
        "state_dir": "tmp/phone/state",
        "timestamp_skew_seconds": 300,
        "nonce_ttl_seconds": 900,
        "allow_cidrs": ["127.0.0.1/32","127.0.0.0/8","10.0.0.0/8","172.16.0.0/12","192.168.0.0/16","::1/128","fe80::/10","fc00::/7"]
    }

def allowed(remote, allow):
    try:
        ip = ipaddress.ip_address(remote)
    except Exception:
        return False
    nets = []
    for c in allow:
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
    auth = request.headers.get("Authorization","")
    if not auth.startswith("Bearer "):
        return jsonify({"error":"missing_bearer"}), 401
    token = auth.split(" ",1)[1].strip()
    if not cfg.get("token"):
        return jsonify({"error":"server_token_not_configured"}), 401
    if token != cfg["token"]:
        return jsonify({"error":"bad_token"}), 401
    remote = request.remote_addr or ""
    if not allowed(remote, cfg.get("allow_cidrs",[])):
        return jsonify({"error":"ip_not_allowed","ip":remote}), 401
    data = request.get_json(silent=True) or {}
    try:
        ts = int(data.get("timestamp",0))
    except Exception:
        ts = 0
    nonce = str(data.get("nonce","")).strip()
    now = int(time.time()); skew = int(cfg.get("timestamp_skew_seconds",300))
    if not (now - skew <= ts <= now + skew):
        return jsonify({"error":"timestamp_out_of_range","now":now,"ts":ts,"skew":skew}), 400
    if len(nonce) < 8:
        return jsonify({"error":"bad_nonce"}), 400
    os.makedirs(cfg["state_dir"], exist_ok=True)
    os.makedirs(cfg["approvals_dir"], exist_ok=True)
    nonces_path = os.path.join(cfg["state_dir"],"nonces_micro.json")
    try:
        with _lock:
            try:
                seen = json.load(open(nonces_path,"r",encoding="utf-8"))
                if not isinstance(seen,dict): seen={}
            except Exception:
                seen = {}
            cutoff = now - int(cfg.get("nonce_ttl_seconds",900))
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
    fname = os.path.join(cfg["approvals_dir"], f"approve_{now}_{nonce}.json")
    try:
        open(fname,"w",encoding="utf-8").write(json.dumps({"action":data.get("action"),"data":data.get("data"),"timestamp":ts,"nonce":nonce}))
    except Exception as e:
        return jsonify({"error":"filedrop_failed","detail":str(e)}), 500
    return jsonify({"ok":True,"nonce":nonce})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8778, debug=False)

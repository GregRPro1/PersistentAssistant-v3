import os, time, json, ipaddress, threading
from flask import Flask, request, jsonify
ROOT = os.path.dirname(os.path.abspath(__file__))
APPROVALS_DIR = os.path.join(ROOT, "tmp", "phone", "approvals")
STATE_DIR     = os.path.join(ROOT, "tmp", "phone", "state")
os.makedirs(APPROVALS_DIR, exist_ok=True); os.makedirs(STATE_DIR, exist_ok=True)
ALLOW = ["127.0.0.1/32","127.0.0.0/8","10.0.0.0/8","172.16.0.0/12","192.168.0.0/16","::1/128","fe80::/10","fc00::/7"]
TS_SKEW = 300; NONCE_TTL = 900; _lock = threading.Lock()
def load_token():
    t = os.getenv("PHONE_APPROVALS_TOKEN", "")
    try:
        p = os.path.join(ROOT, "config", "phone_approvals.yaml")
        if os.path.exists(p):
            for ln in open(p,"r",encoding="utf-8"):
                s=ln.strip()
                if s.startswith("token:"):
                    v=s.split(":",1)[1].strip()
                    if v[:1] == "\"" and v[-1:] == "\"": v=v[1:-1]
                    if not t: t=v
                    break
    except Exception: pass
    return t
def allowed(remote):
    try: ip = ipaddress.ip_address(remote)
    except Exception: return False
    nets=[]
    for c in ALLOW:
        try: nets.append(ipaddress.ip_network(c, strict=False))
        except Exception: pass
    return any(ip in n for n in nets) if nets else True
app = Flask(__name__)
@app.get("/phone/ping")
def ping(): return jsonify({"ok":True,"t":int(time.time())})
@app.get("/phone/health")
def health(): return jsonify({"ok":True,"has_token":bool(load_token())})
@app.post("/phone/approve")
def approve():
    token = load_token()
    auth = request.headers.get("Authorization","")
    if not auth.startswith("Bearer "): return jsonify({"error":"missing_bearer"}), 401
    client_tok = auth.split(" ",1)[1].strip()
    if not token: return jsonify({"error":"server_token_not_configured"}), 401
    if client_tok != token: return jsonify({"error":"bad_token"}), 401
    remote = request.remote_addr or ""
    if not allowed(remote): return jsonify({"error":"ip_not_allowed","ip":remote}), 401
    data = request.get_json(silent=True) or {}
    try: ts = int(data.get("timestamp",0))
    except Exception: ts = 0
    nonce = str(data.get("nonce","")).strip()
    now = int(time.time())
    if not (now-TS_SKEW <= ts <= now+TS_SKEW): return jsonify({"error":"timestamp_out_of_range","now":now,"ts":ts,"skew":TS_SKEW}), 400
    if len(nonce) < 8: return jsonify({"error":"bad_nonce"}), 400
    nonces_path = os.path.join(STATE_DIR, "nonces.json")
    try:
        with _lock:
            try:
                seen = json.load(open(nonces_path,"r",encoding="utf-8"))
                if not isinstance(seen,dict): seen={}
            except Exception: seen={}
            cutoff = now - NONCE_TTL
            for k in list(seen.keys()):
                try:
                    if int(seen[k]) < cutoff: del seen[k]
                except Exception: del seen[k]
            if nonce in seen: return jsonify({"error":"replay"}), 409
            seen[nonce]=now
            open(nonces_path,"w",encoding="utf-8").write(json.dumps(seen))
    except Exception as e: return jsonify({"error":"nonce_store_failed","detail":str(e)}), 500
    try:
        fn = os.path.join(APPROVALS_DIR, f"approve_{now}_{nonce}.json")
        open(fn,"w",encoding="utf-8").write(json.dumps({"action":data.get("action"),"data":data.get("data"),"timestamp":ts,"nonce":nonce}))
    except Exception as e: return jsonify({"error":"filedrop_failed","detail":str(e)}), 500
    return jsonify({"ok":True,"nonce":nonce})
if __name__ == "__main__": app.run(host="0.0.0.0", port=8770, debug=False)

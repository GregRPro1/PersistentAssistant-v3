from __future__ import annotations
import json, os, pathlib, datetime, yaml, hashlib
from flask import Flask, request, jsonify

ROOT = pathlib.Path(__file__).resolve().parents[1]
CFG = ROOT / "config" / "phone" / "phone.yaml"

def load_cfg():
    if CFG.exists():
        with open(CFG, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}

def make_preview():
    # Summarize latest feedback pack pointer + model/plan summaries if available
    data = {}
    latest_ptr = ROOT / "tmp" / "feedback"  # list latest pack
    try:
        packs = sorted([p for p in (latest_ptr.glob("pack_*.zip"))], key=lambda p: p.stat().st_mtime, reverse=True)
        data["latest_pack"] = str(packs[0]) if packs else None
    except Exception as e:
        data["latest_pack_error"] = str(e)

    # Summary line if tool exists
    try:
        from tools.model_summary_line import summary_line
        data["ai_summary"] = summary_line()
    except Exception as e:
        data["ai_summary_error"] = str(e)

    # Plan current/next if tool exists
    try:
        from tools.show_next_step import get_current_next
        cur, nxt = get_current_next()
        data["plan_current"] = cur
        data["plan_next"] = nxt
    except Exception as e:
        data["plan_error"] = str(e)

    data["ts"] = datetime.datetime.utcnow().isoformat()+"Z"
    return data

def authorized(req, token):
    hdr = req.headers.get("X-Phone-Token","")
    return token and hdr and hdr == token

def create_app():
    app = Flask(__name__)
    cfg = load_cfg()
    token = str(cfg.get("token",""))
    host = str(cfg.get("host","127.0.0.1"))
    port = int(cfg.get("port", 8770))

    @app.get("/phone/ping")
    def phone_ping():
        return jsonify({"ok": True, "service":"PHONE", "ts": datetime.datetime.utcnow().isoformat()+"Z"})

    @app.get("/phone/digest")
    def phone_digest():
        nonlocal token
        if not authorized(request, token):
            return jsonify({"ok": False, "error":"unauthorized"}), 401
        return jsonify({"ok": True, "digest": make_preview()})

    # convenience route to read token hash locally (not exposed in digest)
    @app.get("/phone/token_hash")
    def phone_token_hash():
        nonlocal token
        h = hashlib.sha256(token.encode("utf-8")).hexdigest() if token else ""
        return jsonify({"ok": True, "sha256": h})

    app.config["PHONE_HOST"] = host
    app.config["PHONE_PORT"] = port
    return app

if __name__=="__main__":
    app = create_app()
    app.run(host=app.config["PHONE_HOST"], port=app.config["PHONE_PORT"])
# === BEGIN PHONE PWA SERVE + CORS ===
try:
    from flask import send_from_directory, request
except Exception:
    send_from_directory = None
    request = None

try:
    @app.after_request
    def add_cors_headers(resp):
        try:
            origin = request.headers.get("Origin", "*") if request else "*"
            resp.headers["Access-Control-Allow-Origin"] = origin
            resp.headers["Access-Control-Allow-Headers"] = "Content-Type,X-Phone-Token"
            resp.headers["Vary"] = "Origin"
        except Exception:
            pass
        return resp
except Exception:
    pass

import os
PWA_DIR = os.path.join(os.path.dirname(__file__), "phone_static")

if send_from_directory:
    @app.route("/phone/app")
    def phone_app():
        return send_from_directory(PWA_DIR, "index.html")

    @app.route("/phone/static/<path:fname>")
    def phone_static(fname):
        return send_from_directory(PWA_DIR, fname)
# === END PHONE PWA SERVE + CORS ===
# === BEGIN PHONE OPTIONS ===
if send_from_directory:
    @app.route("/phone/options")
    def phone_options():
        return send_from_directory(PWA_DIR, "options.json")
# === END PHONE OPTIONS ===
# === BEGIN PHONE APPROVE ===
def _latest_pack_path():
    import glob, os
    fb = os.path.normpath(os.path.join(TMP_DIR, "feedback"))
    if not os.path.isdir(fb): return None
    cands = []
    for pat in ("pack_*.zip","pack_apply_pack_*.zip"):
        cands.extend(glob.glob(os.path.join(fb, pat)))
    if not cands: return None
    cands.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return os.path.normpath(cands[0])

def _config_token():
    try:
        import yaml
        cfg = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "config", "phone", "phone.yaml"))
        with open(cfg, "r", encoding="utf-8") as f:
            d = yaml.safe_load(f) or {}
        return d.get("token")
    except Exception:
        return None

if jsonify:
    @app.route("/phone/approve", methods=["POST"])
    def phone_approve():
        tok = _config_token()
        hdr = request.headers.get("X-Phone-Token", "")
        if not tok or hdr != str(tok):
            return jsonify({"ok": False, "error": "unauthorized"}), 401
        try:
            data = request.get_json(silent=True) or {}
            choice = data.get("choice") or data.get("phrase")
            payload = {
                "choice": choice,
                "received_at": datetime.datetime.utcnow().isoformat()+"Z",
                "user_agent": request.headers.get("User-Agent",""),
                "remote_addr": request.remote_addr,
            }
            os.makedirs(APPROVE_DIR, exist_ok=True)
            with open(os.path.join(APPROVE_DIR, f"approval_{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"), "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            with open(os.path.join(APPROVE_DIR, "latest.json"), "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            return jsonify({"ok": True, "stored": True, "echo": payload})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/phone/latest_pack")
    def phone_latest_pack():
        p = _latest_pack_path()
        return jsonify({"ok": bool(p), "latest_pack": p})
# === END PHONE APPROVE ===

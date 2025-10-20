#!/usr/bin/env python3
from __future__ import annotations
import os, json, time, subprocess, urllib.request
from pathlib import Path
from flask import Flask, render_template, jsonify, request

APP = Flask(__name__, template_folder="templates", static_folder="static")
REPO = Path(__file__).resolve().parents[2]
OPS = REPO / "reports" / "ops"; OPS.mkdir(parents=True, exist_ok=True)
LOG = OPS / "supervisor.log"
SUP = "http://127.0.0.1:6060"
TJSON = OPS / "tunnel.json"
OPS_STATUS = OPS / "ops_status.json"
PLAN_PATHS = [REPO/"reports/plan/current_plan.json", OPS_STATUS, REPO/"reports/plan/active_plan.json"]

def _get(u,t=1.0,d=None):
    try:
        with urllib.request.urlopen(u, timeout=t) as r:
            if 200<=r.status<300: return json.loads(r.read().decode())
    except: pass
    return d

def _read(p:Path, d=None):
    try: return json.loads(p.read_text("utf-8"))
    except: return d

@APP.route("/")
def index(): return render_template("index.html")

@APP.route("/api/supervisor")
def api_sup(): return jsonify(_get(f"{SUP}/status", d={"healthy":False,"services":{}}))

@APP.route("/api/tunnel")
def api_tunnel(): return jsonify(_read(TJSON, {"hostname":None,"updated_ts":None}))

@APP.route("/api/log_tail")
def api_log():
    n=int(request.args.get("n","6000"))
    if not LOG.exists(): return jsonify({"text":""})
    with open(LOG,"rb") as f:
        f.seek(0,2); size=f.tell(); f.seek(max(0,size-n),0)
        return jsonify({"text": f.read().decode("utf-8","ignore")})

@APP.route("/api/plan")
def api_plan():
    # Try known paths in order. If using ops_status.json, expect {"plan": {...}}
    for p in PLAN_PATHS:
        data = _read(p, {})
        if not data: continue
        if p == OPS_STATUS: data = data.get("plan", {})
        if data: return jsonify(data)
    return jsonify({"name": None, "phase": None, "status": "unknown", "notes": []})

@APP.route("/api/plan/restart", methods=["POST"])
def api_plan_restart():
    _get(f"{SUP}/control?service=planrefresher&action=restart", t=1.0, d=None)
    return jsonify({"ok":True})

# WhatsApp quick send (uses scripts/phone/whatsapp_notify.py env vars)
@APP.route("/api/tunnel/send_now", methods=["POST"])
def api_send_now():
    t=_read(TJSON,{}); h=t.get("hostname")
    if not h: return jsonify({"ok":False,"err":"no_hostname"}), 400
    cmd=[os.getenv("PYTHON","python"), str(REPO/"scripts/phone/whatsapp_notify.py"), f"PAL Tunnel: {h}"]
    try:
        r=subprocess.run(cmd, cwd=str(REPO), capture_output=True, timeout=20)
        return jsonify({"ok": r.returncode==0, "rc": r.returncode, "out": r.stdout.decode(errors="ignore"), "err": r.stderr.decode(errors="ignore")})
    except Exception as e:
        return jsonify({"ok":False,"err":str(e)}), 500

def main():
    import argparse
    ap=argparse.ArgumentParser(); ap.add_argument("--host",default="0.0.0.0"); ap.add_argument("--port",type=int,default=5070)
    a=ap.parse_args(); APP.run(host=a.host, port=a.port, debug=False, threaded=True)
if __name__=="__main__": main()

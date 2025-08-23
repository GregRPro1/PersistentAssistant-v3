# tools/leb_server.py
from __future__ import annotations
import os, sys, threading, subprocess, time
from datetime import datetime
from flask import Flask, request, jsonify

APP = Flask(__name__)
LOG_LOCK = threading.Lock()
LOGS: list[dict] = []
STARTED = datetime.utcnow().isoformat() + "Z"
VERSION = "0.1"

def _add_log(kind: str, msg: str) -> None:
    with LOG_LOCK:
        LOGS.append({"ts": datetime.utcnow().isoformat()+"Z", "kind": kind, "msg": msg})
        # Keep last 500 lines to bound memory
        if len(LOGS) > 500:
            del LOGS[: len(LOGS) - 500]

@APP.get("/ping")
def ping():
    return jsonify({"ok": True, "service": "LEB", "version": VERSION, "started": STARTED})

@APP.post("/run")
def run():
    data = request.get_json(silent=True) or {}
    cmd = data.get("cmd")
    if not cmd or not isinstance(cmd, str):
        return jsonify({"ok": False, "error": "missing cmd"}), 400

    _add_log("run", f"cmd={cmd!r}")
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        _add_log("done", f"rc={p.returncode}")
        return jsonify({
            "ok": True,
            "rc": p.returncode,
            "stdout": p.stdout,
            "stderr": p.stderr
        })
    except Exception as e:
        _add_log("error", f"{type(e).__name__}: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500

@APP.get("/logs")
def logs():
    with LOG_LOCK:
        return jsonify({"ok": True, "lines": LOGS})

if __name__ == "__main__":
    # Default host/port via env or args later if needed
    port = int(os.environ.get("LEB_PORT", "8765"))
    _add_log("start", f"LEB start 127.0.0.1:{port}")
    APP.run(host="127.0.0.1", port=port)

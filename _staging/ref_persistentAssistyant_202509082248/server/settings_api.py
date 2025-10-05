from __future__ import annotations
from flask import Flask, request, jsonify
from tools.py.agentic.project_config import get_auto_revise_limits, set_auto_revise, load_tracker

app = Flask(__name__)

@app.get("/settings/auto_revise")
def get_ar():
    lim = get_auto_revise_limits()
    cfg = load_tracker()
    return jsonify({"ok": True, "limits": lim, "tracker": cfg})

@app.post("/settings/auto_revise")
def set_ar():
    j = request.get_json(force=True, silent=True) or {}
    en  = j.get("enabled")
    di  = j.get("default_iters")
    mx  = j.get("ui_soft_max")
    cfg = set_auto_revise(enabled=en, default_iters=di, ui_soft_max=mx)
    lim = get_auto_revise_limits()
    return jsonify({"ok": True, "limits": lim, "tracker": cfg})

if __name__ == "__main__":
    app.run("127.0.0.1", 5001, debug=False)

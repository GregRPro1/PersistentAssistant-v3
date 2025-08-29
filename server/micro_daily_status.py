from __future__ import annotations
import json
from pathlib import Path
from flask import Blueprint, jsonify

bp = Blueprint("daily_status", __name__)
ROOT = Path(__file__).resolve().parents[1]

@bp.get("/agent/daily_status")
def daily_status():
    p = ROOT / "data" / "status" / "daily_status.json"
    try:
        if not p.exists():
            return jsonify({"ok": False, "error": "daily_status.json not found"}), 404
        data = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return jsonify({"ok": False, "error": "daily_status.json is not a JSON object"}), 500
        data.setdefault("ok", True)
        data.setdefault("last_run", None)
        return jsonify(data)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

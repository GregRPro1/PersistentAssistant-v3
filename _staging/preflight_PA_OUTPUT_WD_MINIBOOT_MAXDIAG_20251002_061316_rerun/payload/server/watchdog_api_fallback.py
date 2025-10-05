# server/watchdog_api_fallback.py
from flask import Blueprint, jsonify

bp = Blueprint('watchdog_api_fallback', __name__, url_prefix='/api/watchdog')

@bp.get('')
def api_root():
    return jsonify({"ok": True, "fallback": True, "msg": "watchdog api fallback active"}), 200

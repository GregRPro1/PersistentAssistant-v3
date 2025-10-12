# _bridge_panel.py — Blueprint for bridge diagnostics
from __future__ import annotations
import json, os
from pathlib import Path
from flask import Blueprint, jsonify, render_template_string

bp = Blueprint('pal_bridge', __name__)

def _repo():
    try:
        return Path(__file__).resolve().parents[2]
    except Exception:
        return Path(r'C:\_Repos\PersistentAssistant')

def _load_json():
    p = _repo()/'reports'/'ops'/'ops_status.json'
    try:
        return json.loads(p.read_text(encoding='utf-8')), str(p)
    except Exception:
        return None, str(p)

def _tail():
    p = _repo()/'tmp'/'bridge_tracker.log'
    try:
        txt = p.read_text(encoding='utf-8').splitlines()[-50:]
        return '\\n'.join(txt), str(p)
    except Exception:
        return '', str(p)

@bp.get('/_pal/bridge')
def panel():
    data, jp = _load_json()
    log, lp = _tail()
    html = f"<h3>Bridge status</h3><p>JSON: {jp}</p>"
    html += "<pre>"+json.dumps(data, indent=2) if data else "<i>no json</i>"
    html += "</pre><p>Log: "+lp+"</p><pre>"+(log or "<i>empty</i>")+"</pre>"
    return html, 200

@bp.get('/_pal/bridge/poll')
def poll():
    data, _ = _load_json()
    return jsonify(data or {}), 200

# server/watchdog_ui_fallback.py
from flask import Blueprint, render_template_string

bp = Blueprint('watchdog_ui_fallback', __name__, url_prefix='/app/watchdog')

TPL = """
<!doctype html>
<title>Watchdog (fallback)</title>
<h1>Watchdog UI (fallback)</h1>
<p>If you see this, the primary UI blueprint wasn't found. Core routing is working.</p>
"""
@bp.get('')
def ui_root():
    return render_template_string(TPL), 200

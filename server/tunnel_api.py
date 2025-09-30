from flask import Blueprint, jsonify
import time
from pathlib import Path
tunnel_bp = Blueprint('tunnel', __name__)
def _status():
    out_dir = Path(__file__).resolve().parent.parent / 'reports' / 'ops'
    url_file = out_dir / 'tunnel_url.txt'
    url = ''
    age_s: int | None = None
    if url_file.exists():
        try:
            url = url_file.read_text(encoding='utf-8').strip()
            age_s = max(0, int(time.time() - url_file.stat().st_mtime))
        except Exception:
            url, age_s = '', None
    return {'url': url, 'running': bool(url), 'age_s': age_s}
@tunnel_bp.route('/api/tunnel', methods=['GET'])
def tunnel_status():
    return jsonify(_status())

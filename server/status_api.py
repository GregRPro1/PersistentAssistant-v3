# server/status_api.py
from flask import Blueprint, jsonify, current_app
from pathlib import Path
import re, datetime as dt

bp = Blueprint('status_api', __name__)
mount_path = '/api/status'

TS_RE = re.compile(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})')

def _repo_root()->Path:
    p = Path(__file__).resolve()
    for _ in range(12):
        if (p/'.git').exists(): return p
        if p.parent==p: break
        p = p.parent
    return Path.cwd()

def _tail_ts(path: Path):
    if not path.exists(): return None
    try:
        txt = path.read_text(encoding='utf-8', errors='ignore').splitlines()
        for line in reversed(txt):
            m = TS_RE.match(line.strip())
            if m:
                return dt.datetime.strptime(m.group(1), '%Y-%m-%d %H:%M:%S')
    except Exception:
        return None
    return None

def _age_str(ts):
    if not ts: return None
    delta = dt.datetime.utcnow() - ts
    s = int(delta.total_seconds())
    h, rem = divmod(s, 3600)
    m, _ = divmod(rem, 60)
    if h>0: return f'{h}h {m}m'
    return f'{m}m'

@bp.get('/overview')
def overview():
    root = _repo_root()
    mounts = [str(r) for r in current_app.url_map.iter_rules()]
    # Presence checks
    has_mobile = any('/app/' in r for r in mounts)
    has_control = any('/control/' in r for r in mounts)
    has_upload = any(r.endswith('/api/upload/pack') for r in mounts) or any('/api/upload' in r for r in mounts)
    has_jobs = any('/api/jobs/' in r for r in mounts)

    # Logs
    pack_log = root / 'reports' / 'ops' / 'pack_fetcher.log'
    email_log = root / 'reports' / 'ops' / 'email_watch.log'
    pack_ts = _tail_ts(pack_log)
    email_ts = _tail_ts(email_log)

    checks = {
        'server': {'ok': True},
        'mobile': {'ok': has_mobile},
        'control': {'ok': has_control},
        'upload_api': {'ok': has_upload},
        'jobs_api': {'ok': has_jobs},
        'pack_fetcher': {'ok': pack_ts is not None, 'last': pack_ts.isoformat() if pack_ts else None, 'age': _age_str(pack_ts)},
        'email_watcher': {'ok': email_ts is not None, 'last': email_ts.isoformat() if email_ts else None, 'age': _age_str(email_ts)},
    }
    ok = all(v.get('ok') for v in checks.values() if v is not None)
    return jsonify({'ok': ok, 'checks': checks, 'routes': mounts})

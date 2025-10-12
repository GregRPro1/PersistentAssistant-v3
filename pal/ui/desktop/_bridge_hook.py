# _bridge_hook.py — PAL bridge: emit heartbeat + URLs to reports/ops/ops_status.json and tmp/bridge_tracker.log
from __future__ import annotations
import os, json, time, threading
from pathlib import Path

_REPO = Path(os.environ.get('PA_REPO', r'C:\_Repos\PersistentAssistant'))
_OUT_JSON = _REPO / 'reports' / 'ops' / 'ops_status.json'
_LOG = _REPO / 'tmp' / 'bridge_tracker.log'
_REPO.mkdir(parents=True, exist_ok=True)
(_REPO/'reports'/'ops').mkdir(parents=True, exist_ok=True)
(_REPO/'tmp').mkdir(parents=True, exist_ok=True)

def _read_url_candidates():
    cand = [
        _REPO/'tmp'/'tracker_tunnel_url.txt',
        _REPO/'tmp'/'dev_tunnel_url.txt',
        _REPO/'tmp'/'tunnel_url.txt',
    ]
    urls = {}
    for p in cand:
        try:
            if p.exists():
                t = p.read_text(encoding='utf-8').strip()
                if t:
                    if 'tracker' in p.name: urls['tracker']=t
                    elif 'dev' in p.name: urls['dev']=t
                    else: urls.setdefault('unknown', t)
        except Exception: pass
    return urls

def _append_log(msg: str):
    try:
        _LOG.write_text((_LOG.read_text(encoding='utf-8') if _LOG.exists() else '') + msg + '\n', encoding='utf-8')
    except Exception:
        try:
            with _LOG.open('a', encoding='utf-8') as f: f.write(msg + '\n')
        except Exception:
            pass

def _loop():
    while True:
        payload = {
            'ts': int(time.time()),
            'heartbeat': { 'tracker': 'alive' },
            'env': {'PAL_MASTER': os.environ.get('PAL_MASTER'), 'PAL_CHILD': os.environ.get('PAL_CHILD')},
            'urls': _read_url_candidates(),
        }
        try:
            _OUT_JSON.write_text(json.dumps(payload, indent=2), encoding='utf-8')
            _append_log(f"[Bridge] update sent ts={payload['ts']} urls={payload['urls']}")
        except Exception as e:
            _append_log(f"[Bridge][ERR] {e!r}")
        time.sleep(5)

_started = False
def start_bridge():
    global _started
    if _started: return
    _started = True
    t = threading.Thread(target=_loop, name='PAL-Bridge', daemon=True)
    t.start()

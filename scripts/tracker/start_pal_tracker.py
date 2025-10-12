from __future__ import annotations
import os, sys, time, json, subprocess, threading
from pathlib import Path

REPO = Path(os.environ.get('PA_REPO', r'C:\_Repos\PersistentAssistant')).resolve()
PY   = sys.executable or "python"
TRACKER = REPO / 'pal' / 'ui' / 'desktop' / 'pal_tracker.py'
LOG_DIR = REPO / 'tmp'
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / 'bridge_tracker.log'
OPS_DIR = REPO / 'reports' / 'ops'
OPS_DIR.mkdir(parents=True, exist_ok=True)
OPS_JSON = OPS_DIR / 'ops_status.json'

def _append(msg: str):
    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    with LOG_FILE.open('a', encoding='utf-8') as f:
        f.write(f"[{ts}] {msg}\n")

def _read_url_candidates():
    urls = {}
    for name in ('tracker_tunnel_url.txt', 'dev_tunnel_url.txt', 'tunnel_url.txt'):
        p = REPO/'tmp'/name
        if p.exists():
            try:
                v = p.read_text(encoding='utf-8').strip()
                if v:
                    key = 'tracker' if 'tracker' in name else ('dev' if 'dev' in name else 'unknown')
                    urls[key] = v
            except Exception:
                pass
    return urls

def _emit_ops():
    payload = {
        'ts': int(time.time()),
        'heartbeat': {'tracker':'alive'},
        'env': {'PAL_MASTER': os.environ.get('PAL_MASTER'), 'PAL_CHILD': os.environ.get('PAL_CHILD')},
        'urls': _read_url_candidates(),
    }
    OPS_JSON.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    _append(f"[Bridge] ops_status updated: {payload['urls']}")

def _hb_loop():
    while True:
        try:
            _emit_ops()
        except Exception as e:
            _append(f"[Bridge][ERR] {e!r}")
        time.sleep(5)

def main():
    if not TRACKER.exists():
        _append(f"[ERR] tracker not found at {TRACKER}")
        sys.exit(2)
    _append(f"[Start] launching {TRACKER}")
    t = threading.Thread(target=_hb_loop, name='PAL-Bridge-HB', daemon=True)
    t.start()
    # Launch tracker and mirror stdout/stderr into our log
    proc = subprocess.Popen([PY, str(TRACKER)], cwd=str(TRACKER.parent), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        for line in proc.stdout:
            _append(line.rstrip())
    except Exception:
        pass
    rc = proc.wait()
    _append(f"[Exit] tracker rc={rc}")
    sys.exit(rc)

if __name__ == '__main__':
    main()

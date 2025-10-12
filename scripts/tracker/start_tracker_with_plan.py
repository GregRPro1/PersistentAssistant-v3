from __future__ import annotations
import os, sys, json, time, subprocess, signal
from pathlib import Path

REPO = Path(os.environ.get('PA_REPO', r'C:\\_Repos\\PersistentAssistant')).resolve()
os.environ.setdefault('PAL_PLAN', str(REPO / 'config' / 'reliability_plan.yaml'))
PLAN = os.environ['PAL_PLAN']

STATE_DIR = REPO / '_state'; STATE_DIR.mkdir(parents=True, exist_ok=True)
TMP_DIR = REPO / 'tmp'; TMP_DIR.mkdir(parents=True, exist_ok=True)
LOG = TMP_DIR / 'bridge_tracker.log'

def _log(msg: str):
    ts = time.strftime('%H:%M:%S')
    try:
        with LOG.open('a', encoding='utf-8') as f:
            f.write(f'[TrackerWrap {ts}] {msg}\\n')
    except Exception:
        pass

pre = {'ts': int(time.time()), 'selected_plan': 'Phase-R1 (pre)'}
(STATE_DIR/'plan_status.json').write_text(json.dumps(pre, indent=2), encoding='utf-8')
_log(f'start with plan={PLAN}')

target = REPO/'pal'/'ui'/'desktop'/'pal_tracker.py'
if not target.exists():
    _log(f'ERR tracker not found at {target}')
    print(f'[ERR] tracker not found at {target}'); sys.exit(2)

proc = subprocess.Popen([sys.executable, str(target)], cwd=str(target.parent))
_log(f'spawned pid={proc.pid}')
try:
    rc = proc.wait()
    _log(f'exit rc={rc}')
    sys.exit(rc)
except KeyboardInterrupt:
    _log('keyboard interrupt -> terminate child')
    try:
        proc.send_signal(signal.CTRL_BREAK_EVENT if hasattr(signal, "CTRL_BREAK_EVENT") else signal.SIGTERM)
    except Exception:
        proc.terminate()
    try:
        proc.wait(timeout=10)
    except Exception:
        pass
    sys.exit(130)

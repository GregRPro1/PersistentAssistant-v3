from __future__ import annotations
import os, json, time, threading
from pathlib import Path

REPO = Path(os.environ.get('PA_REPO', r'C:\\_Repos\\PersistentAssistant')).resolve()
PLAN_ENV = os.environ.get('PAL_PLAN') or str(REPO / 'config' / 'reliability_plan.yaml')
STATE_DIR = REPO / '_state'
TMP_DIR = REPO / 'tmp'
STATE_DIR.mkdir(parents=True, exist_ok=True)
TMP_DIR.mkdir(parents=True, exist_ok=True)
LOG = TMP_DIR / 'bridge_tracker.log'

def _log(msg: str):
    ts = time.strftime('%H:%M:%S')
    try:
        with LOG.open('a', encoding='utf-8') as f:
            f.write(f'[PlanLoader {ts}] {msg}\\n')
    except Exception:
        pass

def parse_plan_text(txt: str) -> dict:
    # minimal YAML subset; tolerate plain text
    data = {'id': 'Phase-R1', 'title': 'Plan', 'items': []}
    for line in txt.splitlines():
        s = line.strip()
        if s.startswith('id:'): data['id'] = s.split(':',1)[1].strip()
        elif s.startswith('title:'): data['title'] = s.split(':',1)[1].strip()
    return data

def load_plan(path: str | None = None) -> dict:
    p = Path(path or PLAN_ENV)
    if not p.exists():
        _log(f'plan missing: {p}')
        return {'id':'Phase-R1','items':[]}
    try:
        txt = p.read_text(encoding='utf-8', errors='ignore')
    except Exception as e:
        _log(f'read err: {e!r}'); txt = ''
    return parse_plan_text(txt)

def emit_status(plan: dict) -> None:
    payload = {'ts': int(time.time()), 'selected_plan': plan.get('id'), 'title': plan.get('title')}
    (STATE_DIR/'plan_status.json').write_text(json.dumps(payload, indent=2), encoding='utf-8')
    _log(f'emit selected_plan={payload["selected_plan"]}')

_started = False
def install():
    global _started
    if _started: 
        _log('install called again; ignoring'); 
        return
    _started = True
    _log(f'install; PLAN_ENV={PLAN_ENV}')
    plan = load_plan(PLAN_ENV)
    emit_status(plan)
    def loop():
        while True:
            try:
                emit_status(plan)
            except Exception as e:
                _log(f'emit err: {e!r}')
            time.sleep(5)
    t = threading.Thread(target=loop, name='PAL-PlanStatus', daemon=True)
    t.start()

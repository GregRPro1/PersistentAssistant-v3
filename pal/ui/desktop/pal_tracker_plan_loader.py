# pal_tracker_plan_loader.py — minimal, non-invasive plan loader
from __future__ import annotations
import os, json, time
from pathlib import Path

REPO = Path(os.environ.get('PA_REPO', r'C:\\_Repos\\PersistentAssistant')).resolve()
PLAN_ENV = os.environ.get('PAL_PLAN') or str(REPO / 'config' / 'reliability_plan.yaml')
STATE_DIR = REPO / '_state'
TMP_DIR = REPO / 'tmp'
STATE_DIR.mkdir(parents=True, exist_ok=True)
TMP_DIR.mkdir(parents=True, exist_ok=True)

def _log(msg: str):
    try:
        with (REPO/'tmp'/'bridge_tracker.log').open('a', encoding='utf-8') as f:
            f.write(f"[PlanLoader] {msg}\n")
    except Exception:
        pass

def load_plan(path: str | None = None) -> dict | None:
    p = Path(path or PLAN_ENV)
    if not p.exists():
        _log(f"plan missing: {p}")
        return None
    try:
        import yaml  # optional; fallback to naive parse if missing
        data = yaml.safe_load(p.read_text(encoding='utf-8'))
    except Exception:
        # naive YAML subset: extremely small
        data = {'id':'Phase-R1', 'items':[]}
        for line in p.read_text(encoding='utf-8', errors='ignore').splitlines():
            if line.strip().startswith('id:'):
                data['id'] = line.split(':',1)[1].strip()
    return data

def emit_status(plan: dict | None):
    payload = {
        'ts': int(time.time()),
        'selected_plan': (plan or {}).get('id') if isinstance(plan, dict) else None
    }
    (STATE_DIR/'plan_status.json').write_text(json.dumps(payload, indent=2), encoding='utf-8')
    _log(f"selected_plan={payload['selected_plan']}")

def install():
    plan = load_plan(PLAN_ENV)
    emit_status(plan)

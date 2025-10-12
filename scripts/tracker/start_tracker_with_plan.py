from __future__ import annotations
import os, sys, json, time, subprocess
from pathlib import Path

REPO = Path(os.environ.get('PA_REPO', r'C:\\_Repos\\PersistentAssistant')).resolve()
os.environ.setdefault('PAL_PLAN', str(REPO / 'config' / 'reliability_plan.yaml'))
PLAN = os.environ['PAL_PLAN']

STATE_DIR = REPO / '_state'; STATE_DIR.mkdir(parents=True, exist_ok=True)
pre = {'ts': int(time.time()), 'selected_plan': 'Phase-R1 (pre)'}
(STATE_DIR/'plan_status.json').write_text(json.dumps(pre, indent=2), encoding='utf-8')

target = REPO/'pal'/'ui'/'desktop'/'pal_tracker.py'
print(f'[Tracker] Starting with plan={PLAN} target={target}')
if not target.exists():
    print(f'[ERR] tracker not found at {target}'); sys.exit(2)

rc = subprocess.call([sys.executable, str(target)], cwd=str(target.parent))
sys.exit(rc)

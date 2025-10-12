from __future__ import annotations
import os, sys, subprocess
from pathlib import Path

REPO = Path(os.environ.get('PA_REPO', r'C:\\_Repos\\PersistentAssistant')).resolve()
os.environ.setdefault('PAL_PLAN', str(REPO / 'config' / 'reliability_plan.yaml'))
target = REPO/'pal'/'ui'/'desktop'/'pal_tracker.py'
if not target.exists():
    print(f'[ERR] tracker not found at {target}'); sys.exit(2)
print(f'[Tracker] Launch with plan: {os.environ.get('PAL_PLAN')}')
sys.exit(subprocess.call([sys.executable, str(target)], cwd=str(target.parent)))

from __future__ import annotations
import json, time
from pathlib import Path
import subprocess, sys

def repo()->Path:
    try:
        p = subprocess.run(['git','rev-parse','--show-toplevel'], capture_output=True, text=True, timeout=3)
        if p.returncode==0 and p.stdout.strip(): return Path(p.stdout.strip())
    except Exception: pass
    return Path(r'C:\_Repos\PersistentAssistant')

def main()->int:
    r = repo()
    f = r/'_state'/'plan_status.json'
    if not f.exists():
        print(f'[MISS] {f}'); return 2
    data = json.loads(f.read_text(encoding='utf-8'))
    plan = data.get('selected_plan')
    print('selected_plan=', plan)
    if plan: return 0
    return 3

if __name__=='__main__':
    raise SystemExit(main())

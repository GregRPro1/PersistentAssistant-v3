from __future__ import annotations
from pathlib import Path
import json, time, subprocess, sys

def repo():
    try:
        p = subprocess.run(['git','rev-parse','--show-toplevel'], capture_output=True, text=True, timeout=3)
        if p.returncode==0 and p.stdout.strip(): return Path(p.stdout.strip())
    except Exception: pass
    return Path(r'C:\_Repos\PersistentAssistant')

def main()->int:
    r = repo()
    f = r/'_state'/'plan_status.json'
    log = r/'tmp'/'bridge_tracker.log'
    if f.exists():
        print('[plan_status.json]'); print(f.read_text(encoding='utf-8'))
    else:
        print(f'[MISS] {f}')
    if log.exists():
        print('[bridge_tracker.log tail]'); print('\\n'.join(log.read_text(encoding='utf-8', errors='ignore').splitlines()[-30:]))
    else:
        print(f'[MISS] {log}')
    return 0

if __name__=='__main__':
    raise SystemExit(main())

from __future__ import annotations
import json, time, sys
from pathlib import Path

REPO = Path(r'C:\\_Repos\\PersistentAssistant').resolve()
f = REPO/'_state'/'plan_status.json'
for i in range(12):
    if f.exists():
        data = json.loads(f.read_text(encoding='utf-8'))
        sel = data.get('selected_plan','')
        print('selected_plan=', sel)
        if sel and '(pre)' not in sel:
            print('[OK] plan promoted')
            sys.exit(0)
    time.sleep(1)
print('[STALE] plan not promoted in time'); sys.exit(2)

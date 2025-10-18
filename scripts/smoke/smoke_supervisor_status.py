#!/usr/bin/env python3
import json, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATUS = ROOT / "reports" / "ops" / "ops_status.json"

def main() -> int:
    if not STATUS.exists():
        print("[FAIL] status missing"); return 2
    try:
        d = json.loads(STATUS.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[FAIL] cannot parse: {e}"); return 3
    ts = None
    for k in ("timestamp","updated_ts","last_update_ts","heartbeat_ts","last_heartbeat_ts"):
        v = d.get(k)
        if isinstance(v,(int,float)): ts = float(v); break
    mtime = STATUS.stat().st_mtime
    now = time.time()
    age = now - (ts if ts else mtime)
    if age <= 90:
        print("[OK] supervisor healthy"); return 0
    else:
        print(f"[FAIL] status too old: age={age:.1f}s"); return 4

if __name__ == "__main__":
    raise SystemExit(main())

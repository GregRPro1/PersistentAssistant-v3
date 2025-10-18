#!/usr/bin/env python3
from __future__ import annotations
import json, sys, time
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[2]
STATE_P = ROOT / "_state" / "plan_status.json"
GREEN_S = 15
WARN_S = 60

def read_json(p: Path) -> Optional[dict[str, Any]]:
    try:
        with p.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def extract_ts(d: dict[str, Any]) -> Optional[float]:
    for k in ["updated_ts", "last_update_ts", "last_heartbeat_ts"]:
        if k in d:
            v = d[k]
            if isinstance(v, (int,float)):
                return float(v)
    return None

def age_seconds(ts: Optional[float], p: Path) -> float:
    now = time.time()
    if ts is not None and 0 < ts < now + 86400*365:
        return max(0.0, now - ts)
    try:
        return max(0.0, now - p.stat().st_mtime)
    except Exception:
        return float('inf')

def main() -> int:
    if not STATE_P.exists():
        print(f"[FAIL] Missing {STATE_P}")
        return 2
    data = read_json(STATE_P)
    if data is None:
        print(f"[FAIL] Cannot parse JSON: {STATE_P}")
        return 3
    ts = extract_ts(data)
    age = age_seconds(ts, STATE_P)

    if age <= GREEN_S:
        print("[OK] plan_status fresh")
        return 0
    elif age <= WARN_S:
        print(f"[WARN] plan_status stale: age={age:.1f}s")
        return 0
    else:
        print(f"[FAIL] plan_status too old: age={age:.1f}s (> {WARN_S}s)")
        return 4

if __name__ == "__main__":
    sys.exit(main())

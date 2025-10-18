#!/usr/bin/env python3
from __future__ import annotations
import json, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATUS = ROOT / "reports" / "ops" / "ops_status.json"

def main() -> int:
    if not STATUS.exists():
        print(f"[FAIL] Missing {STATUS}")
        return 2
    try:
        data = json.loads(STATUS.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[FAIL] Cannot parse {STATUS}: {e}")
        return 3
    ts = data.get("timestamp", 0)
    age = time.time() - float(ts) if ts else float("inf")
    healthy = bool(data.get("healthy", False))
    if age > 30:
        print(f"[FAIL] status too old: age={age:.1f}s")
        return 4
    if not healthy:
        print(f"[FAIL] supervisor reports unhealthy")
        return 5
    print("[OK] supervisor healthy")
    return 0

if __name__ == "__main__":
    sys.exit(main())

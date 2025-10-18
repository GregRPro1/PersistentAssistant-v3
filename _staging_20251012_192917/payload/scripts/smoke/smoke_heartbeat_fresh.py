#!/usr/bin/env python3
"""
Smoke: Some heartbeat JSON exists and is fresh.
Search order:
- reports/ops/heartbeat.json
- reports/ops/ops_status.json
- _state/bridge_heartbeat.json
Freshness thresholds: green <= 30s, warn <= 90s, fail > 90s
"""
from __future__ import annotations
import json, sys, time
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[2]
CANDIDATES = [
    ROOT / "reports" / "ops" / "heartbeat.json",
    ROOT / "reports" / "ops" / "ops_status.json",
    ROOT / "_state" / "bridge_heartbeat.json",
]
GREEN_S = 30
WARN_S = 90

def read_json(p: Path) -> Optional[dict[str, Any]]:
    try:
        with p.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def extract_ts(d: dict[str, Any]) -> Optional[float]:
    for k in ["last_heartbeat_ts", "heartbeat_ts", "updated_ts", "updated_at"]:
        if k in d:
            v = d[k]
            if isinstance(v, (int, float)):
                return float(v)
            if isinstance(v, str):
                import re
                m = re.search(r"(\d{10,})", v)
                if m:
                    return float(m.group(1))
    return None

def age_seconds(ts: Optional[float], p: Path) -> float:
    now = time.time()
    if ts is not None and 0 < ts < now + 86400*365:
        return max(0.0, now - ts)
    try:
        return max(0.0, now - p.stat().st_mtime)
    except Exception:
        return float("inf")

def main() -> int:
    found = None
    data = None
    for p in CANDIDATES:
        if p.exists():
            found = p
            data = read_json(p)
            if data is not None:
                break
    if found is None:
        print("[FAIL] No heartbeat/status JSON found in candidates.")
        for p in CANDIDATES:
            print(f" - {p}")
        return 2
    if data is None:
        print(f"[FAIL] Cannot parse JSON in {found}")
        return 3

    ts = extract_ts(data)
    age = age_seconds(ts, found)

    if age <= GREEN_S:
        print("[OK] heartbeat fresh")
        return 0
    elif age <= WARN_S:
        print(f"[WARN] heartbeat stale: age={age:.1f}s")
        return 0
    else:
        print(f"[FAIL] heartbeat too old: age={age:.1f}s (> {WARN_S}s) [{found.name}]")
        return 4

if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Smoke: Bridge status JSON exists, parses, and is fresh enough.
- Primary: reports/ops/ops_status.json
- Freshness: green <= 30s, warn <= 90s, fail > 90s
- Uses JSON ts fields if present; falls back to file mtime.
"""
from __future__ import annotations
import json, sys, time
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[2]
STATUS_P = ROOT / "reports" / "ops" / "ops_status.json"
GREEN_S = 30
WARN_S = 90

def read_json(p: Path) -> Optional[dict[str, Any]]:
    try:
        with p.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def extract_ts(d: dict[str, Any]) -> Optional[float]:
    """
    Try multiple keys; accept epoch seconds or ISO-like strings containing digits.
    """
    candidates = ["last_heartbeat_ts", "updated_ts", "updated_at", "heartbeat_ts"]
    for k in candidates:
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
    if ts is not None and ts > 0 and ts < now + 86400*365:
        return max(0.0, now - ts)
    # fallback on file mtime
    try:
        return max(0.0, now - p.stat().st_mtime)
    except Exception:
        return float("inf")

def main() -> int:
    if not STATUS_P.exists():
        print(f"[FAIL] Missing {STATUS_P}")
        return 2
    data = read_json(STATUS_P)
    if data is None:
        print(f"[FAIL] Cannot parse JSON: {STATUS_P}")
        return 3
    ts = extract_ts(data)
    age = age_seconds(ts, STATUS_P)

    if age <= GREEN_S:
        print("[OK] bridge status fresh")
        return 0
    elif age <= WARN_S:
        print(f"[WARN] bridge status stale: age={age:.1f}s")
        return 0
    else:
        print(f"[FAIL] bridge status too old: age={age:.1f}s (> {WARN_S}s)")
        return 4

if __name__ == "__main__":
    sys.exit(main())

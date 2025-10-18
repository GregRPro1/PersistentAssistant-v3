#!/usr/bin/env python3
from __future__ import annotations
import time, json, os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "_state" / "plan_status.json"

def write_plan():
    STATE.parent.mkdir(parents=True, exist_ok=True)
    ts = time.time()
    payload = {
        "selected_plan": "Phase-R1",
        "updated_ts": ts,
        "tasks": ["13A – Extraction & watchdog applier ✅",
                  "13B – Tracker & Bridge UI ✅",
                  "13C – Supervisor Consolidation ▶️"]
    }
    tmp = STATE.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    os.replace(tmp, STATE)

def main(interval: int = 10):
    try:
        while True:
            write_plan()
            time.sleep(interval)
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()

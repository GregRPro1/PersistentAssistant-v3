#!/usr/bin/env python3
from __future__ import annotations
import time, json, argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OPS = ROOT / "reports" / "ops" / "ops_status.json"

def emit_once(status: str = "ok"):
    OPS.parent.mkdir(parents=True, exist_ok=True)
    now = time.time()
    payload = {
        "component": "bridge",
        "status": status,
        "healthy": (status == "ok"),
        "updated_ts": now,
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
        "heartbeat_ts": now,
    }
    tmp = OPS.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(OPS)
    print(f"[OK] emitted -> {OPS}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--loop", type=int, default=10, help="seconds; 0 = once")
    args = ap.parse_args()
    if args.loop and args.loop > 0:
        while True:
            emit_once("ok")
            time.sleep(args.loop)
    else:
        emit_once("ok")

if __name__ == "__main__":
    main()

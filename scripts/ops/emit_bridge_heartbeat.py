#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OPS_DIR = ROOT / "reports" / "ops"
OPS_STATUS = OPS_DIR / "ops_status.json"
HEARTBEAT = OPS_DIR / "heartbeat.json"

def now_payload():
    ts = time.time()
    return {
        "component": "bridge",
        "status": "ok",
        "last_heartbeat_ts": ts,
        "updated_ts": ts,
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts)),
    }

def write_json(p: Path, data):
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, p)

def emit_once():
    payload = now_payload()
    write_json(OPS_STATUS, payload)
    write_json(HEARTBEAT, payload)
    print(f"[OK] emitted -> {OPS_STATUS}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--loop", type=int, default=0, help="Emit every N seconds")
    args = ap.parse_args()
    if args.loop and args.loop > 0:
        try:
            while True:
                emit_once()
                time.sleep(args.loop)
        except KeyboardInterrupt:
            print("[OK] stopped")
    else:
        emit_once()

if __name__ == "__main__":
    main()

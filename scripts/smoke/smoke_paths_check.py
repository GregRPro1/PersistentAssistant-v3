#!/usr/bin/env python3
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
expect = [
    ROOT / "scripts" / "ops" / "emit_bridge_heartbeat.py",
    ROOT / "scripts" / "smoke" / "smoke_bridge_status.py",
    ROOT / "scripts" / "smoke" / "smoke_heartbeat_fresh.py",
]
missing = [str(p) for p in expect if not p.exists()]
if missing:
    print("[FAIL] Missing paths:")
    for m in missing:
        print(" -", m)
    sys.exit(2)
print("[OK] All expected paths present")

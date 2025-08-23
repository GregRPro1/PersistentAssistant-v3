from __future__ import annotations
# --- PA_ROOT_IMPORT ---
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# --- /PA_ROOT_IMPORT ---
import subprocess, sys, os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOGS = ROOT / "logs"
OUT  = LOGS / "test_results.txt"
LOGS.mkdir(parents=True, exist_ok=True)

cmd = [sys.executable, "-m", "pytest", "-q"]
p = subprocess.run(cmd, text=True, capture_output=True)
OUT.write_text((p.stdout or "") + "\n" + (p.stderr or ""), encoding="utf-8")

print("== TESTS DONE ==")
print(p.stdout.strip())
if p.returncode != 0:
    print("== FAILURES DETECTED ==")
    print(p.stderr.strip())

sys.exit(p.returncode)

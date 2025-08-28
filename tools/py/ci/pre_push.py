#!/usr/bin/env python
from __future__ import annotations
import sys, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PY = sys.executable

def run(cmd: list[str]) -> int:
    p = subprocess.Popen(cmd, cwd=str(ROOT))
    return p.wait()

def main() -> int:
    return run([PY, "tools/py/ci/ci_check.py"])

if __name__ == "__main__":
    sys.exit(main())

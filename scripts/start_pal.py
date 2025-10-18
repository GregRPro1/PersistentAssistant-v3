#!/usr/bin/env python3
from __future__ import annotations
import subprocess, sys
from pathlib import Path

# Repo root = parent of 'scripts' directory
ROOT = Path(__file__).resolve().parents[1]

venv_py = ROOT / ".venv" / "Scripts" / "python.exe"
py = str(venv_py) if venv_py.exists() else sys.executable

subprocess.run([py, "scripts/supervisor/supervisor.py"], cwd=ROOT, check=False)

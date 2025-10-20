#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
NAME_PAT = re.compile(r"(phone|mobile|twilio|sms|whatsapp|telegram|signal|approval|remote[_-]?control|phone[_-]?bridge)", re.I)
EXCLUDE_DIRS = {".git",".venv","__pycache__","node_modules","dist","build","releases","_staging",".idea",".vscode"}

hits = []
for p in ROOT.rglob("*"):
    if p.is_dir(): 
        continue
    if any(part in EXCLUDE_DIRS for part in p.parts):
        continue
    if NAME_PAT.search(p.as_posix()):
        hits.append(p.relative_to(ROOT).as_posix())

print("[INFO] candidates:", len(hits))
for s in sorted(hits)[:50]:
    print(" -", s)

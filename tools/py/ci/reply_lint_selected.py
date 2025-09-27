#!/usr/bin/env python
from __future__ import annotations
import sys, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PY   = sys.executable

EXCLUDE_DIRS = {".git", ".venv", "venv", "node_modules", "tmp", "__pycache__"}
EXCLUDE_FILES = {"OpenAI_Interaction.md"}  # contains intentional anti-patterns

def is_excluded(p: Path) -> bool:
    parts = set(p.parts)
    if parts & EXCLUDE_DIRS: return True
    if p.name in EXCLUDE_FILES: return True
    return False

def main() -> int:
    md_files = [p for p in ROOT.rglob("*.md") if not is_excluded(p)]
    if not md_files:
        print("No Markdown files to lint (after exclusions).")
        return 0
    failures = 0
    for md in sorted(md_files):
        rc = subprocess.run([PY, "tools/py/lint/reply_lint.py", "--path", str(md)], cwd=str(ROOT)).returncode
        if rc != 0:
            failures += 1
    if failures:
        print(f"SUMMARY: {failures} file(s) failed reply-lint.")
        return 2
    print("SUMMARY: reply-lint clean.")
    return 0

if __name__ == "__main__":
    sys.exit(main())

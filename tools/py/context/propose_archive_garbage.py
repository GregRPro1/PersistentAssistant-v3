#!/usr/bin/env python3
import fnmatch
from pathlib import Path

PATTERNS = [
    "*.bak", "*.bak.*", "*.orig", "*.rej", "*.tmp", "*~", "*.swp", "*.swo",
    ".DS_Store", "Thumbs.db", "*.LOCAL.*", "*.REMOTE.*", "*.BACKUP.*", "*.BASE.*",
]

EXCLUDE = {".git",".venv","_archive","_context","node_modules",".idea",".vscode",
           "__pycache__",".pytest_cache",".mypy_cache","dist","build","out"}

def main():
    repo = Path(".").resolve()
    ctx  = Path("_context/PAL20251020B"); ctx.mkdir(parents=True, exist_ok=True)
    out  = ctx / "archive_noise_candidates.txt"

    cands = []
    for p in repo.rglob("*"):
        if not p.is_file(): continue
        parts = p.relative_to(repo).parts
        if any(x in EXCLUDE for x in parts): continue
        name = p.name
        if any(fnmatch.fnmatch(name, pat) for pat in PATTERNS):
            cands.append(p.relative_to(repo).as_posix())

    cands = sorted(set(cands))
    out.write_text("\n".join(cands), encoding="utf-8")
    print(f"[OK] noise candidates: {len(cands)} -> {out}")
    print(f"Append to archive list:\n  type {out} >> _context\\PAL20251020B\\archive_candidates.txt")

if __name__ == "__main__":
    main()

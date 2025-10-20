#!/usr/bin/env python3
from pathlib import Path

PROTECT = {".git",".venv","_archive","_context","node_modules",".idea",".vscode",
           "__pycache__",".pytest_cache",".mypy_cache","dist","build","out"}

def main():
    repo = Path(".").resolve()
    removed = 0
    changed = True
    while changed:
        changed = False
        for d in sorted((p for p in repo.rglob("*") if p.is_dir()),
                        key=lambda p: len(p.parts), reverse=True):
            parts = d.relative_to(repo).parts
            if not parts or any(x in PROTECT for x in parts): continue
            try:
                if next(d.iterdir(), None) is None:
                    d.rmdir()
                    print(f"[PRUNE] {d.as_posix()}"); removed += 1; changed = True
            except Exception:
                pass
    print(f"[DONE] dirs_pruned={removed}")

if __name__ == "__main__":
    main()

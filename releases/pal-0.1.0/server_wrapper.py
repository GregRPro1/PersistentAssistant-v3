"""
Robust wrapper: prints PAL banner, then locates and runs your dev server.
Search order:
  1) <repo>/current/server.py
  2) <repo>/releases/current/server.py
  3) <repo>/server.py
"""
from utils.context_banner import print_banner
print_banner("PAL")

import pathlib, runpy, sys, os

def find_repo_root(start: pathlib.Path) -> pathlib.Path:
    # Walk up until we find a .git or a folder named 'PersistentAssistant'
    p = start
    for _ in range(6):
        if (p/".git").exists():
            return p
        p = p.parent
    # Fallback to two levels up from this file (old behavior)
    return start.parents[1]

here = pathlib.Path(__file__).resolve()
repo_root = find_repo_root(here)

candidates = [
    repo_root / "current" / "server.py",
    repo_root / "releases" / "current" / "server.py",
    repo_root / "server.py",
]

for path in candidates:
    if path.exists():
        runpy.run_path(str(path), run_name="__main__")
        sys.exit(0)

print(f"[server_wrapper] ERROR: Could not locate server.py. Tried:")
for p in candidates:
    print(f" - {p}")
sys.exit(2)

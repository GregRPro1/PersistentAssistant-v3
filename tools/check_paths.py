from __future__ import annotations
# --- PA_ROOT_IMPORT ---
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# --- /PA_ROOT_IMPORT ---
import os, yaml
from tools.path_utils import abspath, chdir_root

def main():
    chdir_root()
    idx = abspath("project_index.yaml")
    ok = True
    if os.path.exists(idx):
        d = yaml.safe_load(open(idx,"r",encoding="utf-8")) or {}
        files = (d.get("project_index") or {}).get("files") or {}
        for key, meta in files.items():
            p = meta.get("path","")
            if not p: 
                print(f"[WARN] entry '{key}' missing path")
                ok = False; continue
            ap = abspath(*p.replace("\\","/").split("/"))
            if not os.path.exists(ap):
                print(f"[MISS] {key} → {ap}")
                ok = False
    print("[PATHS OK]" if ok else "[PATHS ISSUES]")
    return 0 if ok else 1

if __name__ == "__main__":
    raise SystemExit(main())

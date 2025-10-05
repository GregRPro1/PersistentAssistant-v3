from __future__ import annotations
import argparse, os, shutil, time, pathlib

def main():
    ap = argparse.ArgumentParser(description="Install NEW file if target missing; back up if present.")
    ap.add_argument("--path", required=True, help="Target file path")
    ap.add_argument("--new", required=True, help="Path to new file content")
    args = ap.parse_args()

    target = pathlib.Path(args.path)
    newf = pathlib.Path(args.new)
    if not newf.exists():
        print(f"[ABORT] new file missing: {newf}")
        return 2
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        ts = time.strftime("%Y%m%d_%H%M%S")
        backup = f"{target}.bak.{ts}"
        shutil.copy2(target, backup)
        shutil.copy2(newf, target)
        print(f"OK: replaced {target}\n backup: {backup}")
        return 0
    else:
        shutil.copy2(newf, target)
        print(f"OK: installed NEW {target}")
        return 0

if __name__ == "__main__":
    raise SystemExit(main())

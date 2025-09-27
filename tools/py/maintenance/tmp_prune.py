from __future__ import annotations
import argparse, pathlib, time, os, sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
TMP  = ROOT / "tmp"

def iter_files(base: pathlib.Path):
    for p in base.rglob("*"):
        if p.is_file():
            yield p

def prune(days:int, apply:bool, include_backups:bool):
    cutoff = time.time() - days*86400
    deleted = 0; kept = 0
    for f in iter_files(TMP):
        rel = f.relative_to(ROOT).as_posix()
        if not include_backups and rel.startswith("tmp/backups/"):
            kept += 1
            continue
        try:
            st = f.stat()
        except OSError:
            continue
        if st.st_mtime < cutoff:
            if apply:
                try: f.unlink()
                except OSError: pass
            deleted += 1
        else:
            kept += 1
    return deleted, kept

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=14, help="age threshold (days)")
    ap.add_argument("--apply", action="store_true", help="actually delete (default: dry-run)")
    ap.add_argument("--include-backups", action="store_true", help="also prune tmp/backups")
    args = ap.parse_args()
    TMP.mkdir(parents=True, exist_ok=True)
    deleted, kept = prune(args.days, args.apply, args.include_backups)
    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"[tmp_prune] {mode}: deleted={deleted}, kept={kept}, days={args.days}, include_backups={args.include_backups}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

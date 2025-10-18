#!/usr/bin/env python3
r"""
apply_pack_debug.py — verbose, self-healing ZIP applier for PA

What it does (default behavior):
1) Lists ZIP entries (first 200) so we can see what’s inside.
2) Extracts to a temp dir.
3) Detects the true payload root (works with/without wrapper dirs).
4) Copies files into the repo, flattening any leading 'payload/'.
5) Auto-rescues any stray 'repo_root/payload/' by moving contents into place.
6) Prints final existence checks for key targets (or custom ones via --expect).

Usage:
  python .\scripts\apply_pack_debug.py -ZipPath "C:\Users\...\Downloads\PACK.zip"

Useful flags:
  --list-only            Only list ZIP entries, don’t copy.
  --rescue-payload       After copy, move repo-root 'payload/' contents into place.
  --expect REL [--expect REL ...]  Extra post-apply existence checks.
"""
from __future__ import annotations
import argparse, os, shutil, sys, tempfile, zipfile
from pathlib import Path
from typing import Iterable, List

MAX_LIST = 200

def list_zip(zf: zipfile.ZipFile, max_items: int = MAX_LIST) -> None:
    names = zf.namelist()
    print(f"[ZIP] Entries: {len(names)}")
    for s in names[:max_items]:
        print(f"  - {s}")
    if len(names) > max_items:
        print(f"  ... (+{len(names)-max_items} more)")

def detect_payload_root(tmp_dir: Path) -> Path | None:
    # Prefer exact 'payload' at root
    if (tmp_dir / "payload").exists():
        return tmp_dir / "payload"
    # Any nested '/payload' dir
    nests = [p for p in tmp_dir.rglob("payload") if p.is_dir()]
    if nests:
        # Choose the shortest path (closest to root)
        return sorted(nests, key=lambda p: len(p.parts))[0]
    # Fallback: wrapper containing 'scripts'
    for d in tmp_dir.iterdir():
        if d.is_dir() and (d / "scripts").exists():
            return d
    return None

def iter_files(root: Path) -> Iterable[Path]:
    for p in root.rglob("*"):
        if p.is_file():
            yield p

def copy_flatten_payload(payload_root: Path, repo_root: Path) -> int:
    """
    Ensure output paths are like:
      payload/scripts/x.py -> repo_root/scripts/x.py
      scripts/x.py         -> repo_root/scripts/x.py
    If a file path starts with 'payload/', strip that segment.
    """
    count = 0
    for src in iter_files(payload_root):
        rel = src.relative_to(payload_root)
        parts = rel.parts
        if parts and parts[0].lower() == "payload":
            rel = Path(*parts[1:]) if len(parts) > 1 else Path()
        dst = repo_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        tmp = dst.with_suffix(dst.suffix + ".applied_tmp")
        shutil.copy2(src, tmp)
        os.replace(tmp, dst)
        print(f"[COPY] {src} -> {dst}  [EXISTS={dst.exists()}]")
        count += 1
    return count

def rescue_repo_payload(repo_root: Path) -> int:
    """If repo_root/payload exists, move its contents into place (flatten)."""
    pay = repo_root / "payload"
    if not pay.exists():
        print("[RESCUE] No repo-root 'payload/' to rescue.")
        return 0
    moved = 0
    for src in list(pay.rglob("*")):
        if src.is_file():
            rel = src.relative_to(pay)
            dst = repo_root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            print(f"[RESCUE] {src} -> {dst}")
            moved += 1
    # Clean empty dirs
    for d in sorted([x for x in pay.rglob("*") if x.is_dir()], reverse=True):
        try: d.rmdir()
        except OSError: pass
    try: pay.rmdir()
    except OSError: pass
    print(f"[RESCUE] Moved {moved} files from repo-root 'payload/'")
    return moved

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("-ZipPath", required=True, help="Path to the pack ZIP")
    ap.add_argument("-RepoRoot", default=str(Path(__file__).resolve().parents[1]), help="Repo root (optional)")
    ap.add_argument("--list-only", action="store_true", help="Only list ZIP entries, do not copy")
    ap.add_argument("--rescue-payload", action="store_true", help="Rescue repo-root 'payload/' after copy")
    ap.add_argument("--expect", action="append", default=[], help="Relative paths to verify after apply")
    args = ap.parse_args()

    zip_path = Path(args.ZipPath).expanduser().resolve()
    repo_root = Path(args.RepoRoot).resolve()
    print(f"[INFO] RepoRoot: {repo_root}")
    print(f"[INFO] ZipPath : {zip_path}")

    if not zip_path.exists():
        print(f"[FAIL] Zip not found: {zip_path}")
        return 2
    if not repo_root.exists():
        print(f"[FAIL] Repo root not found: {repo_root}")
        return 3

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        with zipfile.ZipFile(zip_path, "r") as z:
            list_zip(z)
            if args.list_only:
                print("[DONE] list-only — no extraction performed.")
                return 0
            z.extractall(td)
        print(f"[EXTRACT] TempDir: {td}")

        pr = detect_payload_root(td)
        if pr is None:
            print("[FAIL] Could not locate payload root in ZIP")
            return 4
        print(f"[DETECT] Payload root: {pr}")

        count = copy_flatten_payload(pr, repo_root)
        print(f"[OK] Applied files: {count}")

    if args.rescue_payload:
        rescue_repo_payload(repo_root)

    # Default checks (we care about these commonly)
    defaults = [
        "scripts/ops/emit_bridge_heartbeat.py",
        "scripts/smoke/smoke_bridge_status.py",
        "scripts/smoke/smoke_heartbeat_fresh.py",
    ]
    checks: List[str] = defaults + [x for x in args.expect if x not in defaults]
    missing = []
    for rel in checks:
        p = repo_root / rel
        print(f"[CHECK] {rel} => {p.exists()}  ({p})")
        if not p.exists():
            missing.append(rel)
    if missing:
        print(f"[WARN] Missing expected paths: {missing}")
        return 5

    print("[DONE] apply_pack_debug completed")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

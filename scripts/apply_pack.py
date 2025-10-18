#!/usr/bin/env python3
"""
apply_pack.py — High-verbosity, self-healing applier.
- Always prints ZIP entries and chosen payload root.
- Flattens nested 'payload/' correctly.
- If files land under repo-root 'payload/', auto-rescues into place.
- Prints per-dir copy counts and final existence checks.
"""
from __future__ import annotations
import os, shutil, sys, tempfile, zipfile
from pathlib import Path
from typing import Iterable

def list_zip(zf: zipfile.ZipFile, max_items: int = 30) -> None:
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
    # Prefer any nested '/payload' dir
    for p in tmp_dir.rglob("payload"):
        if p.is_dir():
            return p
    # Fallback: wrapper containing scripts/
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
    Copies files so that 'payload/scripts/x.py' -> 'repo_root/scripts/x.py'.
    If payload_root itself is .../payload, we strip that level.
    If payload_root is wrapper (contains 'scripts' but not named 'payload'), we treat it as payload root.
    """
    count = 0
    # If payload_root endswith 'payload', then rel is relative to that 'payload' dir.
    for src in iter_files(payload_root):
        rel = src.relative_to(payload_root)
        # If rel begins with 'payload/', strip that leading segment (handles double-nesting zips)
        parts = rel.parts
        if parts and parts[0].lower() == "payload":
            rel = Path(*parts[1:]) if len(parts) > 1 else Path()
        dst = repo_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        tmp = dst.with_suffix(dst.suffix + ".applied_tmp")
        shutil.copy2(src, tmp)
        os.replace(tmp, dst)
        print(f"[COPY] {src} -> {dst}")
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
    # Basic args parsing without argparse to avoid platform quoting issues
    import shlex
    args = sys.argv[1:]
    if "-ZipPath" not in args:
        print("[FAIL] Usage: python .\\scripts\\apply_pack.py -ZipPath \"C:\\path\\pack.zip\"")
        return 2
    zp = Path(args[args.index("-ZipPath")+1]).expanduser().resolve()
    rr = Path(__file__).resolve().parents[1]
    if not zp.exists():
        print(f"[FAIL] Zip not found: {zp}")
        return 2
    print(f"[INFO] RepoRoot: {rr}")
    print(f"[INFO] ZipPath : {zp}")

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        with zipfile.ZipFile(zp, "r") as z:
            list_zip(z)
            z.extractall(td)
        pr = detect_payload_root(td)
        if pr is None:
            print("[FAIL] Could not locate payload root in ZIP")
            return 4
        print(f"[DETECT] Payload root: {pr}")
        count = copy_flatten_payload(pr, rr)
        print(f"[OK] Applied files: {count}")

    # Always attempt rescue if any accidental repo-root 'payload/' remains
    rescue_repo_payload(rr)

    # Post-apply sanity
    checks = [
        "scripts/ops/emit_bridge_heartbeat.py",
        "scripts/smoke/smoke_bridge_status.py",
        "scripts/smoke/smoke_heartbeat_fresh.py",
    ]
    missing = []
    for rel in checks:
        p = rr / rel
        if p.exists():
            print(f"[CHECK][OK]   {rel}")
        else:
            print(f"[CHECK][MISS] {rel}")
            missing.append(rel)
    if missing:
        print(f"[WARN] Missing expected paths: {len(missing)}")
        return 5

    print("[DONE] apply_pack completed")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

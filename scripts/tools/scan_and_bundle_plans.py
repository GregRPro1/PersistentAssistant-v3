#!/usr/bin/env python3
from __future__ import annotations
import argparse, os, sys, time, json, zipfile, hashlib
from pathlib import Path
from typing import List, Dict

ROOT = Path(__file__).resolve().parents[2]

DEFAULT_PATTERNS = [
    "*plan*.yaml",
    "*plans*.yaml",
    "project_plan*.yaml",
    "pal_project_plan.yaml",
    "master_project_tracker.yaml",
    "*tracker*.yaml",
]
# Additional optional files
OPTIONAL_FILES = [
    "_state/plan_status.json",
    "reports/ops/ops_status.json",
    "_context/**/bootstrap.md",
]

IGNORE_DIRS = {
    ".git", ".venv", "__pycache__", "node_modules",
    "_staging", "dist", "build", "releases", ".idea", ".vscode"
}

def is_ignored_dir(p: Path) -> bool:
    parts = set(p.parts)
    return any(part in IGNORE_DIRS for part in parts)

def walk_patterns(root: Path, patterns: List[str]) -> List[Path]:
    found: List[Path] = []
    for pat in patterns:
        for p in root.rglob(pat):
            if p.is_file() and not is_ignored_dir(p.parent):
                found.append(p)
    # de-duplicate while preserving order
    seen = set()
    uniq = []
    for p in found:
        rp = p.resolve()
        if rp in seen: 
            continue
        seen.add(rp); uniq.append(p)
    return uniq

def hash_file(p: Path, algo="sha256", limit_mb: float = 5.0) -> str:
    # Hash small/medium files to help dedupe; skip huge files for speed
    try:
        h = hashlib.new(algo)
        sz = p.stat().st_size
        if sz > limit_mb * 1024 * 1024:
            return f"SKIPPED>{sz}B"
        with p.open("rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception as e:
        return f"ERR:{e}"

def main() -> int:
    ap = argparse.ArgumentParser(description="Scan repo for plan files and bundle them.")
    ap.add_argument("--out", default=None, help="Output zip path (default: repo root / PAL_plan_bundle_<ts>.zip)")
    ap.add_argument("--include-state", action="store_true", help="Include runtime state JSONs (e.g., _state/plan_status.json)")
    ap.add_argument("--extra", action="append", default=[], help="Extra glob(s) to include (relative to repo root)")
    args = ap.parse_args()

    root = ROOT
    ts = time.strftime("%Y%m%d-%H%M%S")
    out_zip = Path(args.out) if args.out else (root / f"PAL_plan_bundle_{ts}.zip")
    manifest_p = root / "reports" / "plan_scan_manifest.json"
    manifest_p.parent.mkdir(parents=True, exist_ok=True)

    patterns = list(DEFAULT_PATTERNS)
    extras = list(args.extra or [])
    if args.include_state:
        patterns.extend(OPTIONAL_FILES)

    # core scan
    files = walk_patterns(root, patterns)
    # explicitly add extras (support dirs/globs)
    for ex in extras:
        for p in root.rglob(ex):
            if p.is_file() and not is_ignored_dir(p.parent):
                files.append(p)
    # de-dupe again
    seen = set(); uniq = []
    for p in files:
        rp = p.resolve()
        if rp in seen: continue
        seen.add(rp); uniq.append(p)

    # Build manifest
    items: List[Dict] = []
    for p in uniq:
        try:
            st = p.stat()
            items.append({
                "path": str(p.relative_to(root)),
                "size": st.st_size,
                "mtime": st.st_mtime,
                "sha256": hash_file(p),
            })
        except FileNotFoundError:
            continue

    # Write manifest
    manifest = {
        "generated_at": time.time(),
        "root": str(root),
        "count": len(items),
        "patterns": patterns,
        "extra": extras,
        "include_state": bool(args.include_state),
        "files": items,
    }
    tmpmf = manifest_p.with_suffix(".json.tmp")
    tmpmf.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    tmpmf.replace(manifest_p)

    # Create bundle zip
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as z:
        # include the manifest for context
        z.writestr("MANIFEST/plan_scan_manifest.json", json.dumps(manifest, indent=2))
        for p in uniq:
            try:
                z.write(p, p.relative_to(root))
            except FileNotFoundError:
                continue

    print(f"[OK] Found {len(items)} file(s).")
    print(f"[OK] Manifest -> {manifest_p}")
    print(f"[OK] Bundle   -> {out_zip}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

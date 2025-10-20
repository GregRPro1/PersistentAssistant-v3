#!/usr/bin/env python3
from __future__ import annotations
import re, zipfile, time, os, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTDIR = ROOT / "reports" / "exports"
OUTDIR.mkdir(parents=True, exist_ok=True)

NAME_PAT = re.compile(r"""(phone|mobile|android|ios|handset|twilio|sms|whatsapp|telegram|signal|webhook|push|notification|notifier|approve|approval|inbox|outbox|bridge[_-]?phone|phone[_-]?bridge|remote[_-]?control|5080|5070|6060)""", re.I)

EXCLUDE_DIRS = {".git",".venv","__pycache__","node_modules","dist","build","releases","_staging",".idea",".vscode"}
CAND_EXT = {".py",".ps1",".sh",".json",".yaml",".yml",".md",".html",".jinja",".jinja2"}

def iter_repo_files():
    for p in ROOT.rglob("*"):
        if p.is_dir(): continue
        if any(part in EXCLUDE_DIRS for part in p.parts): continue
        if p.suffix.lower() not in CAND_EXT: continue
        rel = p.relative_to(ROOT).as_posix()
        if NAME_PAT.search(rel): yield p

def main() -> int:
    hits = list(iter_repo_files())
    ts = time.strftime("%Y%m%d-%H%M%S")
    out_zip = OUTDIR / f"phone_code_snapshot_{ts}.zip"
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as z:
        manifest = []
        for p in hits:
            rel = p.relative_to(ROOT).as_posix()
            z.write(p, rel)
            manifest.append(rel)
        z.writestr("_manifest.json", json.dumps({"count": len(manifest), "files": manifest}, indent=2))
    print(f"[OK] wrote {out_zip} with {len(hits)} files")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

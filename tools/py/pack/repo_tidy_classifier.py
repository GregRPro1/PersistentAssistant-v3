#!/usr/bin/env python3
"""
Repo tidy classifier (read-only)
- Ingests an AST index JSON (from tools\py\pack\ast_indexer.py) and classifies *all* files.
- Uses only stdlib; no destructive actions. Produces CSV + Markdown + text lists for review.

Outputs (under --outdir):
  - <name>_tidy_index.csv         : one row per file with features and the predicted category
  - <name>_tidy_summary.md        : counts, rationale, suggested next steps
  - <name>_groups\*.txt           : per-category file lists (for human review / future automation)

Run example:
  python tools\py\pack\repo_tidy_classifier.py ^
      --ast tmp\logs\sb_ast_now_ast_index.json ^
      --outdir tmp\diagnostics --name tidy_now
"""
from __future__ import annotations

import argparse, csv, json, os, re, subprocess, sys, time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

# ------------- args -------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Classify repo files using AST + heuristics (read-only).")
    p.add_argument("--ast", help="Path to AST JSON produced by tools\\py\\pack\\ast_indexer.py", required=False)
    p.add_argument("--outdir", default="tmp/diagnostics", help="Where reports are written.")
    p.add_argument("--name", default=None, help="Base name for outputs (default: tidy_YYYYMMDD_HHMMSS).")
    p.add_argument("--roots", nargs="*", default=["."], help="Root(s) to scan; defaults to current repo.")
    p.add_argument("--include-ignored", action="store_true",
                   help="Also include files git would normally ignore (build caches, etc.).")
    return p

# ------------- helpers -------------

WIN = os.name == "nt"

def repo_root() -> Path:
    try:
        r = subprocess.run(["git","rev-parse","--show-toplevel"], capture_output=True, text=True, check=True)
        return Path(r.stdout.strip())
    except Exception:
        return Path(".").resolve()

def norm_rel(path: Path, root: Path) -> str:
    try:
        rel = path.resolve().relative_to(root.resolve())
    except Exception:
        rel = path
    s = str(rel)
    return s.replace("\\","/")

def shell_ok(cmd: List[str]) -> Tuple[bool,str]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return True, r.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stdout + e.stderr

def git_tracked_set(root: Path) -> set[str]:
    ok,out = shell_ok(["git","ls-files","-z"])
    if not ok: return set()
    items = [x for x in out.split("\x00") if x]
    return set(x.replace("\\","/") for x in items)

def git_untracked_set(root: Path) -> set[str]:
    ok,out = shell_ok(["git","ls-files","--others","--exclude-standard","-z"])
    if not ok: return set()
    items = [x for x in out.split("\x00") if x]
    return set(x.replace("\\","/") for x in items)

def git_last_commit_epoch(rel: str) -> int:
    ok,out = shell_ok(["git","log","-1","--format=%ct","--",rel])
    if not ok or not out.strip():
        return 0
    try:
        return int(out.strip())
    except Exception:
        return 0

def safe_read_text(p: Path, limit_bytes: int = 512_000) -> str:
    try:
        with open(p, "rb") as fh:
            data = fh.read(limit_bytes)
        return data.decode("utf-8", errors="replace")
    except Exception:
        return ""

def load_ast_index(ast_path: Optional[Path], root: Path) -> Dict[str, Any]:
    """
    Accepts keys as produced by your ast_indexer (either absolute or relative).
    We normalize to repo-relative forward-slash paths.
    """
    if not ast_path or not ast_path.exists():
        return {}
    try:
        raw = json.loads(ast_path.read_text(encoding="utf-8"))
    except Exception:
        return {}

    idx: Dict[str, Any] = {}
    root_s = str(root.resolve()).replace("\\","/")
    for k,v in raw.items():
        key = k.replace("\\","/")
        # strip absolute prefix if present
        if key.startswith(root_s + "/"):
            key = key[len(root_s)+1:]
        idx[key] = v
    return idx

# ------------- classification rules -------------

RE_BACKUP = re.compile(r"(\.bak$|\.old$|~$|\.orig$|\.rej$|\.tmp$| copy(?:\s*\(\d+\))?$)", re.IGNORECASE)
PATCH_EXTS = {".patch",".diff"}
DISABLED_SUFFIX = ".disabled"

GEN_DIRS = {
    "tmp/", "build/", "dist/", "__pycache__/", ".pytest_cache/", ".mypy_cache/",
    ".ruff_cache/", ".tox/", ".eggs/", ".cache/", "node_modules/"
}
DOC_EXTS = {".md",".rst",".adoc"}
CONF_EXTS = {".yml",".yaml",".toml",".ini",".cfg",".json",".xml",".properties",".env"}

def starts_with_any(rel: str, prefixes: List[str]) -> bool:
    return any(rel.lower().startswith(p.lower()) for p in prefixes)

def in_any_dir(rel: str, dirs: List[str]) -> bool:
    rl = rel.lower()
    return any(rl.startswith(d) or f"/{d}" in rl for d in dirs)

def classify_one(rel: str, ext: str, name: str, size: int, text_head: str, ast_info: Any) -> Tuple[str, str]:
    """
    Returns (category, rationale). Categories:
      core, tests, tooling, docs, workflows, patches, backups, generated, configs, web, data, disabled, large_binary, vendor, unknown
    """
    rl = rel.lower()
    # 1) Easy buckets by extension/location
    if rel.endswith(DISABLED_SUFFIX):
        return "disabled", "Filename ends with .disabled"
    if ext in PATCH_EXTS or rl.endswith(".rej"):
        return "patches", "Patch/diff artifact"
    if RE_BACKUP.search(name):
        return "backups", "Backup artifact naming pattern"
    if any(rl.startswith(d) for d in GEN_DIRS) or "/tmp/" in rl or "\\tmp\\" in rel:
        return "generated", "In tmp/ or common build/temp dirs"
    if rl.startswith(".git/"):
        return "generated", "In .git/"
    if "/.venv/" in rl or rl.startswith(".venv/"):
        return "vendor", "In virtual environment"
    if rl.startswith("docs/") or ext in DOC_EXTS or name.lower() in {"readme.md","readme"}:
        return "docs", "Documentation"
    if rl.startswith(".github/workflows/") and ext in {".yml",".yaml"}:
        return "workflows", "GitHub Actions workflow"
    if rl.startswith("tools/") or rl.startswith("scripts/"):
        return "tooling", "Under tools/ or scripts/"
    if "/tests/" in rl or "\\tests\\" in rel or name.startswith("test_") or name.endswith("_test.py"):
        return "tests", "Test naming or path pattern"
    if rl.startswith("web/") or ext in {".html",".htm",".js",".ts",".css",".scss",".vue"}:
        return "web", "Web frontend asset"
    if rl.startswith("data/") or rl.startswith("insights/") or "/insights/" in rl:
        return "data", "Data/insights asset"
    if ext in CONF_EXTS:
        return "configs", "Configuration file"

    # 2) Rough binary/large file detector
    if size >= 25_000_000:
        return "large_binary", "Very large file (>=25MB)"

    # 3) Python specifics using AST / text
    if ext == ".py":
        if ast_info and isinstance(ast_info, dict):
            if "error" in ast_info:
                return "tooling", "Python file with parse error; likely non-core/tool-or-script"
            imps = ast_info.get("imports") or []
            classes = ast_info.get("classes") or {}
            funcs = ast_info.get("functions") or []
            if "__main__" in text_head:
                return "tooling", "Has __main__ guard; likely CLI/tool"
            # Heuristics: server/ or API endpoints look more core
            if rl.startswith("server/") or "flask" in " ".join(imps).lower() or "fastapi" in " ".join(imps).lower():
                return "core", "Server/API-like module (imports include web framework or in server/)"
            if rl.startswith("tools/py/agentic/"):
                return "core", "Agentic pipeline scripts"
            if (classes or funcs) and ("test" not in name.lower()):
                return "core", "Library/module with definitions"
            return "tooling", "Python with few signals of core; likely utility"
        else:
            # If no AST info (non-Python path or AST not provided), fallback to text
            if "__main__" in text_head:
                return "tooling", "Has __main__ guard; likely CLI/tool"
            return "core", "Python file (no AST), defaulting to core"

    # 4) Default buckets
    if ext in {".bat",".ps1",".cmd",".sh"}:
        return "tooling", "Script file"
    if ext in {".png",".jpg",".jpeg",".gif",".svg",".ico",".mp4",".mov",".pdf"}:
        return "web", "Asset/media"
    return "unknown", "No strong signal"

# ------------- main -------------

def main() -> int:
    args = build_parser().parse_args()
    root = repo_root()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    base = args.name or f"tidy_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    groups_dir = outdir / f"{base}_groups"
    groups_dir.mkdir(parents=True, exist_ok=True)

    # Load AST index if provided
    ast_idx = load_ast_index(Path(args.ast), root) if args.ast else {}

    # Git info
    tracked = git_tracked_set(root)
    untracked = git_untracked_set(root) if args.include_ignored else set()

    # Gather files
    roots = [Path(r) for r in args.roots]
    files: List[Path] = []
    for r in roots:
        r = r.resolve()
        for p in r.rglob("*"):
            if p.is_file():
                # Always skip .git internals
                try:
                    rel = norm_rel(p, root)
                    if rel.startswith(".git/"):
                        continue
                    files.append(p)
                except Exception:
                    continue

    # Analyze
    rows: List[Dict[str, Any]] = []
    group_lists: Dict[str, List[str]] = {}
    def add_to_group(cat: str, rel: str):
        group_lists.setdefault(cat, []).append(rel)

    for p in files:
        rel = norm_rel(p, root)
        name = p.name
        ext  = p.suffix.lower()
        size = p.stat().st_size if p.exists() else 0

        # text sample
        text_head = ""
        if ext in {".py",".md",".txt",".json",".yaml",".yml",".js",".ts",".html",".css",".ps1",".bat",".cmd",".sh"}:
            text_head = safe_read_text(p, limit_bytes=128_000)  # enough for signals

        # AST info for this file (repo-relative fwd slashes)
        ast_info = ast_idx.get(rel)

        cat, why = classify_one(rel, ext, name, size, text_head, ast_info)

        is_tracked   = rel in tracked
        is_untracked = rel in untracked
        last_commit  = git_last_commit_epoch(rel) if is_tracked else 0
        last_commit_iso = datetime.utcfromtimestamp(last_commit).isoformat() + "Z" if last_commit else ""

        rows.append({
            "path": rel,
            "category": cat,
            "why": why,
            "ext": ext or "",
            "size_bytes": size,
            "git_tracked": 1 if is_tracked else 0,
            "git_untracked": 1 if is_untracked else 0,
            "git_last_commit_epoch": last_commit,
            "git_last_commit_utc": last_commit_iso,
            "ast_has": 1 if ast_info else 0,
            "ast_error": 1 if isinstance(ast_info, dict) and "error" in ast_info else 0,
        })
        add_to_group(cat, rel)

    # Write CSV
    csv_path = outdir / f"{base}_tidy_index.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()) if rows else
                           ["path","category","why","ext","size_bytes","git_tracked","git_untracked","git_last_commit_epoch","git_last_commit_utc","ast_has","ast_error"])
        w.writeheader()
        for r in rows:
            w.writerow(r)

    # Write group lists
    for cat, items in sorted(group_lists.items()):
        (groups_dir / f"{cat}.txt").write_text("\n".join(sorted(items)), encoding="utf-8")

    # Summary MD
    counts = {k: len(v) for k,v in group_lists.items()}
    total = len(rows)
    md = []
    md.append(f"# Tidy Summary — {base}\n")
    md.append(f"- Scanned files: **{total}**\n")
    md.append(f"- With AST info: **{sum(1 for r in rows if r['ast_has'])}**\n")
    md.append(f"\n## Counts by category\n")
    for k in sorted(counts.keys()):
        md.append(f"- **{k}**: {counts[k]}")
    md.append("\n## Suggested next steps (non-destructive)\n")
    md.append("- Review the text lists under `_groups/` (e.g. `backups.txt`, `patches.txt`, `generated.txt`).")
    md.append("- Anything in **backups/patches/generated/disabled** is usually safe to archive or delete.")
    md.append("- **tooling** is helpful to keep, but see whether any are stale/unreferenced (old POCs, scripts).")
    md.append("- **unknown** deserves a quick manual look; decide keep vs. archive.")
    md.append("- **workflows**: ensure only the intended ones remain active.")
    md.append("\n*(This report is read-only and did not modify the repo.)*\n")
    md_path = outdir / f"{base}_tidy_summary.md"
    md_path.write_text("\n".join(md), encoding="utf-8")

    print(str(csv_path))
    print(str(md_path))
    print(str(groups_dir))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

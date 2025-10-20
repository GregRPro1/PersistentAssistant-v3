#!/usr/bin/env python3
import argparse, csv, json, os, re, shutil, sys, time
from pathlib import Path

HEADER_BEGIN = "RFX-REFORMAT-HEADER-BEGIN"
HEADER_END   = "RFX-REFORMAT-HEADER-END"
SIDECAREXT   = ".refactor.json"

COMMENT_STYLE = {
    ".py":("hash","#"), ".ps1":("hash","#"), ".psm1":("hash","#"), ".sh":("hash","#"),
    ".yaml":("hash","#"), ".yml":("hash","#"), ".toml":("hash","#"), ".ini":("hash","#"),
    ".cfg":("hash","#"), ".txt":("hash","#"), ".md":("html",None),
    ".bat":("bat","REM "), ".cmd":("bat","REM ")
}
TEXT_EXTS = set(COMMENT_STYLE.keys())

def now_utc(): return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
def is_text_ext(p: Path): return p.suffix.lower() in TEXT_EXTS

def load_list(p: Path):
    return [] if not p.exists() else [ln.strip() for ln in p.read_text(encoding="utf-8", errors="ignore").splitlines() if ln.strip()]

def load_csv_reasons(p: Path):
    d = {}
    if not p.exists(): return d
    with p.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            d[row["path"].replace("\\","/")] = row.get("reasons","")
    return d

def build_header_lines(style, meta):
    lines=[]
    if style[0]=="hash":
        pre=style[1]; lines += [f"{pre} {HEADER_BEGIN}"] + [f"{pre} {k}: {v}" for k,v in meta.items()] + [f"{pre} {HEADER_END}",""]
    elif style[0]=="bat":
        pre=style[1]; lines += [f"{pre}{HEADER_BEGIN}"] + [f"{pre}{k}: {v}" for k,v in meta.items()] + [f"{pre}{HEADER_END}",""]
    elif style[0]=="html":
        lines += [f"<!-- {HEADER_BEGIN}"] + [f"{k}: {v}" for k,v in meta.items()] + [f"{HEADER_END} -->",""]
    return "\n".join(lines)

def strip_existing_header(text: str):
    pat = re.compile(r"(?s)^(?:.*?" + re.escape(HEADER_BEGIN) + r".*?" + re.escape(HEADER_END) + r".*?\n+)", re.IGNORECASE)
    return re.sub(pat, "", text, count=1)

def write_header(path: Path, meta: dict):
    style = COMMENT_STYLE.get(path.suffix.lower())
    if not style: return False
    try:
        orig = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False
    header = build_header_lines(style, meta)
    newtxt = header + strip_existing_header(orig)
    path.write_text(newtxt, encoding="utf-8")
    return True

def write_sidecar(json_path: Path, meta: dict):
    side = json_path.with_suffix(json_path.suffix + SIDECAREXT)
    side.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return True

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--context", required=True)
    ap.add_argument("--moves", help="optional YAML path: {moves:[{from:...,to:...}]}")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--verbose", "-v", action="store_true")
    args = ap.parse_args()

    repo = Path(".").resolve()
    ctx  = Path(args.context).resolve()
    logp = repo / "reports" / "ops" / "refactor_apply.log"
    logp.parent.mkdir(parents=True, exist_ok=True)

    def log(msg):
        line = f"{now_utc()} {msg}"
        print(line, flush=True)
        try:
            with logp.open("a", encoding="utf-8") as f: f.write(line+"\n")
        except Exception:
            pass

    inv_csv = ctx / "file_inventory_with_reasons.csv"
    arch_txt = ctx / "archive_candidates.txt"
    keep_txt = ctx / "maintain_in_repo_candidates.txt"
    summary  = ctx / "summary.json"

    if not inv_csv.exists():
        log(f"[ERR] Missing {inv_csv}"); sys.exit(2)

    reasons_map = load_csv_reasons(inv_csv)
    arch_list = set(load_list(arch_txt))
    keep_list = set(load_list(keep_txt))

    # optional moves map
    moves_map = {}
    if args.moves:
        try:
            import yaml
            data = yaml.safe_load(Path(args.moves).read_text(encoding="utf-8"))
            for m in (data.get("moves") or []):
                src = (m.get("from") or "").replace("\\","/").strip()
                dst = (m.get("to") or "").replace("\\","/").strip()
                if src and dst: moves_map[src]=dst
        except Exception as e:
            log(f"[WARN] moves file not loaded: {e}")

    stamp = time.strftime("%Y%m%d")
    arch_root = repo / "_archive" / stamp

    scanned = sorted(reasons_map.keys())
    # UNION of all paths we might need to touch (even if not in CSV)
    paths_union = set(scanned)
    paths_union.update(x.replace("\\", "/") for x in arch_list)
    paths_union.update(x.replace("\\", "/") for x in keep_list)
    paths_union.update(x.replace("\\", "/") for x in moves_map.keys())

    paths_union = sorted(paths_union)

    if args.verbose:
        log(f"[INFO] scanned {len(scanned)} files from {inv_csv}")
        extra = len(paths_union) - len(scanned)
        if extra > 0:
            log(f"[INFO] +{extra} additional paths from archive/keep/moves")

    kept_cnt=moved_cnt=archived_cnt=header_cnt=sidecar_cnt=0
    manifest = {"created_utc": now_utc(), "context_dir": str(ctx), "items":[]}

    for rel in paths_union:
        action = "keep"
        dst_rel = None
        if rel in moves_map: action="move"; dst_rel = moves_map[rel]
        elif rel in arch_list: action="archive"
        elif rel in keep_list: action="keep"

        src = repo / rel
        if not src.exists():
            if args.verbose: log(f"[MISS] {rel} not found")
            continue

        meta = {
            "Refactor-ID": stamp, "Refactor-UTC": now_utc(),
            "Action": action, "Original-Path": rel, "New-Path": rel,
            "Reasons": reasons_map.get(rel,""), "Context-Dir": str(ctx.relative_to(repo)) if str(ctx).startswith(str(repo)) else str(ctx)
        }

        # annotate
        if src.suffix.lower()==".json":
            if not args.dry_run and write_sidecar(src, meta): sidecar_cnt+=1
            elif args.dry_run and args.verbose: log(f"[DRY] sidecar -> {rel}{SIDECAREXT}")
        elif is_text_ext(src):
            if not args.dry_run and write_header(src, meta): header_cnt+=1
            elif args.dry_run and args.verbose: log(f"[DRY] header -> {rel}")

        # act
        if action=="keep":
            kept_cnt+=1
            if args.verbose: log(f"[KEEP] {rel}")
        elif action=="move":
            moved_cnt+=1
            if args.dry_run:
                if args.verbose: log(f"[DRY] MOVE {rel} -> {dst_rel}")
            else:
                dst = repo / dst_rel; dst.parent.mkdir(parents=True, exist_ok=True); shutil.move(str(src), str(dst))
                meta["New-Path"]=dst_rel
                if dst.suffix.lower()==".json": write_sidecar(dst, meta)
                elif is_text_ext(dst): write_header(dst, meta)
                manifest["items"].append({"path":rel,"action":"move","dst":dst_rel,"bytes":dst.stat().st_size})
                if args.verbose: log(f"[MOVE] {rel} -> {dst_rel}")
        elif action=="archive":
            archived_cnt+=1
            if args.dry_run:
                if args.verbose: log(f"[DRY] ARCHIVE {rel}")
            else:
                dst = arch_root / rel; dst.parent.mkdir(parents=True, exist_ok=True); shutil.move(str(src), str(dst))
                meta["New-Path"]=str(dst.relative_to(repo)).replace("\\","/")
                if dst.suffix.lower()==".json": write_sidecar(dst, meta)
                elif is_text_ext(dst): write_header(dst, meta)
                manifest["items"].append({"path":rel,"action":"archive","dst":meta['New-Path'],"bytes":dst.stat().st_size})
                if args.verbose: log(f"[ARCH] {rel} -> {meta['New-Path']}")

    if not args.dry_run and (archived_cnt>0 or moved_cnt>0):
        arch_root.mkdir(parents=True, exist_ok=True)
        (arch_root / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    log(f"[DONE] scanned={len(scanned)} keep={kept_cnt} move={moved_cnt} archive={archived_cnt} headers={header_cnt} sidecars={sidecar_cnt}")
    log(f"[LOG ] {logp}")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, sys, time, zipfile, pathlib, subprocess
from typing import List, Tuple
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

ROOT = pathlib.Path(__file__).resolve().parents[3] if len(pathlib.Path(__file__).resolve().parts) >= 4 else pathlib.Path.cwd()
LOGS = ROOT / "tmp" / "logs"
NOW  = time.strftime("%Y%m%d_%H%M%S")

def _norm_rel(p: pathlib.Path) -> str:
    try: return str(p.resolve().relative_to(ROOT))
    except Exception: return str(p.resolve())

def _ensure_dir(p: pathlib.Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

def _glob_logs() -> List[pathlib.Path]:
    if not LOGS.exists(): return []
    pats = ["*.log","*.out.log","*.err.log","sidecar_*.out.log","sidecar_*.err.log"]
    files: List[pathlib.Path] = []
    for pat in pats: files.extend(sorted(LOGS.glob(pat)))
    return files

def capture_http(label: str, url: str, outdir: pathlib.Path) -> List[pathlib.Path]:
    fn = outdir / f"cap_{label}_http.txt"
    meta = outdir / f"cap_{label}_http.meta.json"
    try:
        req = Request(url, headers={"Cache-Control":"no-store","User-Agent":"pa-support-bundle"})
        with urlopen(req, timeout=15) as r:
            body = r.read()
            status = getattr(r, "status", 200)
            ct = r.headers.get("Content-Type","")
        fn.write_bytes(body)
        meta.write_text(json.dumps({"ok": True, "url": url, "status": int(status), "content_type": ct, "bytes": len(body)}, indent=2))
    except (HTTPError, URLError, Exception) as e:
        fn.write_text(f"[ERROR] {type(e).__name__}: {e}")
        meta.write_text(json.dumps({"ok": False, "url": url, "error": f"{type(e).__name__}: {e}"}, indent=2))
    return [fn, meta]

def capture_cmd(label: str, command: str, outdir: pathlib.Path) -> List[pathlib.Path]:
    out = outdir / f"cap_{label}_cmd.out.txt"
    err = outdir / f"cap_{label}_cmd.err.txt"
    meta = outdir / f"cap_{label}_cmd.meta.json"
    try:
        proc = subprocess.run(command, shell=True, capture_output=True, text=True)
        out.write_text(proc.stdout or "")
        err.write_text(proc.stderr or "")
        meta.write_text(json.dumps({"ok": (proc.returncode==0), "cmd": command, "rc": proc.returncode}, indent=2))
    except Exception as e:
        out.write_text("")
        err.write_text(f"[ERROR] {type(e).__name__}: {e}")
        meta.write_text(json.dumps({"ok": False, "cmd": command, "error": f"{type(e).__name__}: {e}"}, indent=2))
    return [out, err, meta]

def parse_label_pair(s: str) -> Tuple[str,str]:
    if "::" not in s: raise argparse.ArgumentTypeError("expected 'label::value'")
    label, val = s.split("::", 1)
    label = "".join(ch for ch in label.strip() if ch.isalnum() or ch in "-_")
    if not label: raise argparse.ArgumentTypeError("label must not be empty")
    return label, val.strip()

def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    p.add_argument("--outdir", default=str(LOGS), help="Output directory (default: tmp/logs)")
    p.add_argument("--name",   default="support_bundle", help="Base name for files")
    p.add_argument("--add-logs", action="store_true", help="Include recent log files from tmp/logs")
    p.add_argument("--include", action="append", default=[], help="Relative file to include (repeatable)")
    p.add_argument("--capture-http", action="append", default=[], help='Capture URL: \"label::http://…\" (repeatable)')
    p.add_argument("--capture-cmd",  action="append", default=[], help='Capture command: \"label::cmd\" (repeatable)')
    return p

def main() -> int:
    ap = build_arg_parser()
    args = ap.parse_args()

    outdir = pathlib.Path(args.outdir)
    _ensure_dir(outdir)

    ts = NOW
    base = f"{args.name}_{ts}"
    zip_path = outdir / f"{base}.zip"
    manifest = outdir / f"{base}_MANIFEST.json"

    files: List[pathlib.Path] = []

    # explicit includes (relative to repo root)
    for inc in args.include:
        rp = (ROOT / inc).resolve()
        if rp.exists() and rp.is_file():
            files.append(rp)

    # logs
    if args.add_logs:
        files.extend(_glob_logs())

    # captures (write captures directly into tmp/logs then zip them)
    for s in args.capture_http:
        label, url = parse_label_pair(s)
        files.extend(capture_http(label, url, outdir))
    for s in args.capture_cmd:
        label, cmd = parse_label_pair(s)
        files.extend(capture_cmd(label, cmd, outdir))

    # dedupe
    seen = set(); files2: List[pathlib.Path] = []
    for f in files:
        if not f.exists(): continue
        key = str(f.resolve())
        if key in seen: continue
        seen.add(key); files2.append(f)

    if not files2:
        manifest.write_text(json.dumps({"ok": False, "reason":"no_files_to_bundle", "cwd": str(ROOT)}, indent=2))
        print(json.dumps({"ok": False, "reason":"no_files_to_bundle", "cwd": str(ROOT)}))
        return 0

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for f in files2:
            z.write(f, arcname=_norm_rel(f))

    mf = {
        "ok": True,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "zip": str(zip_path),
        "root": str(ROOT),
        "count": len(files2),
        "files": [_norm_rel(p) for p in files2],
        "env": {"python": sys.executable, "cwd": str(ROOT)},
    }
    manifest.write_text(json.dumps(mf, indent=2))
    print(str(zip_path))
    print("MANIFEST:" + str(manifest))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

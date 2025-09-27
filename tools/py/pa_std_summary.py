from __future__ import annotations
import argparse, subprocess, sys, pathlib, re, time, json

ROOT = pathlib.Path(__file__).resolve().parents[2]
PY   = sys.executable

def run(cmd:list[str], cwd: pathlib.Path|None=None, timeout:int|None=None) -> tuple[int,str,str]:
    p = subprocess.run(cmd, cwd=str(cwd or ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    return p.returncode, p.stdout or "", p.stderr or ""

def step(name, cmd):
    rc,out,err = run(cmd)
    print(f"[{name}] rc={rc}")
    if out.strip(): print(out.strip())
    if err.strip(): print(err.strip())
    return rc==0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--level", choices=["quick","standard","deep"], default="standard")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8782)
    args = ap.parse_args()

    ok_all = True
    # 1) Manifest (always)
    ok_all &= step("manifest", [PY, str(ROOT/"tools/file_manifest.py")])
    # 2) Reporters (best-effort)
    ri = ROOT/"tools/py/inventory/report_index.py"
    rh = ROOT/"tools/py/inventory/report_headers.py"
    if ri.exists(): ok_all &= step("report_index", [PY, str(ri)])
    else: print("[report_index] SKIP (missing)")
    if rh.exists(): ok_all &= step("report_headers", [PY, str(rh)])
    else: print("[report_headers] SKIP (missing)")
    # 3) Deep (optional)
    if args.level=="deep":
        ok_all &= step("deep_inventory", [PY, str(ROOT/"tools/deep_inventory.py")])
        ok_all &= step("make_summary",   [PY, str(ROOT/"tools/make_summary.py")])
    # 4) Pack (standard project snapshot)
    ok_all &= step("project_snapshot", [PY, str(ROOT/"tools/py/pa_project_snapshot.py")])

    # Extract PACK path from snapshot output if printed
    # (We also check the latest in tmp/feedback as fallback.)
    pack = None
    feedback = ROOT/"tmp/feedback"
    if feedback.exists():
        zips = sorted(feedback.glob("pack_project_snapshot_*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
        if zips: pack = str(zips[0])

    status = "OK" if ok_all else "WARN summary_steps_failed"
    print(f"PACK: {pack if pack else '[NOT CREATED]'}")
    print(f"STATUS: {status}")
    print("python ./tools/show_next_step.py")
    return 0 if ok_all else 1

if __name__ == "__main__":
    sys.exit(main())

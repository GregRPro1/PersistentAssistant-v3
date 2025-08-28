#!/usr/bin/env python
# daily_dev_loop.py — tiny, phone-friendly daily check
# Pipeline: reply-lint(selected) → mvp_smoke → std_summary → build_catalog → enrich_pack → verify_pack
# Writes: data/status/daily_status.json, and prints a brief one-liner suitable for phone.

import sys, os, json, argparse, subprocess, time
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[3]  # .../PersistentAssistant
PY   = sys.executable

def run(cmd, cwd: Path) -> dict:
    t0 = time.time()
    try:
        p = subprocess.Popen(cmd, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        out, _ = p.communicate()
        rc = p.returncode
    except Exception as e:
        out = f"[EXC] {type(e).__name__}: {e}"
        rc = 99
    ms = int((time.time() - t0) * 1000)
    # capture a short note (first non-empty line)
    note = ""
    for line in (out or "").splitlines():
        s = line.strip()
        if s:
            note = s
            break
    return {"cmd": cmd, "rc": rc, "ms": ms, "note": note, "out": out}

def latest_pack() -> str | None:
    fb = ROOT / "tmp" / "feedback"
    if not fb.exists():
        return None
    zips = sorted(fb.glob("pack_project_snapshot_*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
    return str(zips[0]) if zips else None

def write_json(obj: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["brief","standard","deep"], default="standard",
                    help="Selects summary depth and whether to run std or deep inventory (default: standard)")
    ap.add_argument("--json-out", default=str((ROOT / "data" / "status" / "daily_status.json").as_posix()))
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", default="8782")
    ap.add_argument("--brief", action="store_true", help="Force brief console output")
    args = ap.parse_args()

    os.environ.setdefault("PYTHONWARNINGS", "error::SyntaxWarning")

    steps = []

    # 1) reply-lint (selected files set)
    steps.append(("reply_lint_selected",
                  [PY, "tools/py/ci/reply_lint_selected.py"]))

    # 2) mvp smoke (fast endpoint probe)
    steps.append(("mvp_smoke",
                  [PY, "tools/py/mvp_smoke.py"]))

    # 3) standard or deep summary
    level = "deep" if args.mode == "deep" else "standard"
    steps.append((f"pa_std_summary[{level}]",
                  [PY, "tools/py/pa_std_summary.py", "--level", level]))

    # 4) rebuild tool catalog (talks to agent / routes)
    steps.append(("build_tool_catalog",
                  [PY, "tools/py/registry/build_tool_catalog.py", "--host", args.host, "--port", args.port]))

    # 5) enrich latest pack (inject plan/catalog/reporters)
    steps.append(("enrich_pack",
                  [PY, "tools/py/pack/enrich_pack.py"]))

    # 6) verify the pack contents
    steps.append(("verify_pack",
                  [PY, "tools/py/pack/verify_pack.py", "--include-meta", "--check-insights"]))

    results = []
    overall_rc = 0
    for name, cmd in steps:
        r = run(cmd, ROOT)
        r["name"] = name
        results.append(r)
        if r["rc"] != 0 and overall_rc == 0:
            overall_rc = r["rc"]
            # continue running to collect more context, but remember failure

    # compute brief headline
    ok_count = sum(1 for r in results if r["rc"] == 0)
    total = len(results)
    pack_path = latest_pack() or ""
    status = "OK" if overall_rc == 0 else "FAIL"
    headline = f"DAILY {status}: {ok_count}/{total} stages OK" + (f" | pack: {pack_path}" if pack_path else "")

    # write JSON status for app/GUI
    now = datetime.now(timezone.utc).isoformat()
    status_obj = {
        "id": "daily_dev_loop",
        "ts_utc": now,
        "mode": args.mode,
        "status": status,
        "ok_count": ok_count,
        "total": total,
        "pack": pack_path,
        "steps": [
            {
                "name": r["name"],
                "rc": r["rc"],
                "ms": r["ms"],
                "note": r["note"],
            } for r in results
        ]
    }
    write_json(status_obj, Path(args.json_out))

    # console output
    if args.brief or args.mode == "brief":
        print(headline)
    else:
        print("\n=== Daily Dev Loop ===")
        print(f"{'stage':28} {'rc':>3} {'ms':>6}  note")
        for r in results:
            print(f"{r['name']:28} {r['rc']:>3} {r['ms']:>6}  {r['note']}")
        print(f"\n{headline}")

    # familiar 3-line footer for downstream scripts
    print(f"PACK: {pack_path or '[NONE]'}")
    print(f"STATUS: {status}")
    print("python ./tools/show_next_step.py")

    return 0 if overall_rc == 0 else overall_rc

if __name__ == "__main__":
    sys.exit(main())

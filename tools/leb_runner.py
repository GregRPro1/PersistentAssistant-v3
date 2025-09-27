from __future__ import annotations
import sys, subprocess, json, time, pathlib, shlex

ROOT = pathlib.Path(__file__).resolve().parents[1]
LOGS = ROOT / "logs" / "leb"
LOGS.mkdir(parents=True, exist_ok=True)

# Minimal allow-list for safety
ALLOW = ("python ", "pytest ")

def main() -> int:
    if len(sys.argv) < 2:
        print("usage: python tools/leb_runner.py -- <cmdline>")
        return 2
    if sys.argv[1] != "--":
        print("use -- then the command to run")
        return 2

    # The raw command line string we want to execute
    cmdline = " ".join(sys.argv[2:]).strip()
    if not cmdline.startswith(ALLOW):
        print(f"[BLOCKED] Only commands starting with {ALLOW} are allowed (MVP).")
        return 3

    ts = time.strftime("%Y%m%d_%H%M%S")
    log_path = LOGS / f"leb_{ts}.log"

    # IMPORTANT: pass tokens, not a single string (Windows-safe)
    runner = [sys.executable, str(ROOT / "tools" / "run_with_capture.py"), "--"]
    runner += shlex.split(cmdline)

    try:
        p = subprocess.run(runner, capture_output=True, text=True)
        out = (p.stdout or "") + (("\n" + p.stderr) if p.stderr else "")
        log_path.write_text(out, encoding="utf-8")
        print(json.dumps({
            "ok": (p.returncode == 0),
            "code": p.returncode,
            "log": str(log_path),
            "head": out[:4000]
        }, ensure_ascii=False))
        return p.returncode
    except Exception as e:
        log_path.write_text(str(e), encoding="utf-8")
        print(json.dumps({"ok": False, "error": str(e), "log": str(log_path)}))
        return 1

if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations
import os, sys, subprocess, pathlib, time

ROOT = pathlib.Path(__file__).resolve().parents[1]
PY = sys.executable

def run_guard() -> int:
    # Prefer the gentle guard to avoid any terminal exits
    ps1 = ROOT / "tools" / "gentle_guard.ps1"
    if ps1.exists():
        # Invoke PowerShell to run the gentle guard
        cmd = ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(ps1)]
        p = subprocess.run(cmd, capture_output=True, text=True)
        print(p.stdout, end="")
        if p.stderr:
            print(p.stderr, file=sys.stderr, end="")
        return p.returncode
    # Fallback: call the Python guard directly
    p = subprocess.run([PY, "tools/forbidden_guard.py"], capture_output=True, text=True)
    print(p.stdout, end="")
    if p.stderr:
        print(p.stderr, file=sys.stderr, end="")
    return p.returncode

def main():
    rc = run_guard()
    print(f"[PRE] Guard rc={rc} — continuing (warn-only).")

    # Chain to the real apply_and_pack.py with passthrough args
    ap = ROOT / "tools" / "apply_and_pack.py"
    if not ap.exists():
        print("[PRE] ERROR: tools/apply_and_pack.py not found.", file=sys.stderr)
        return 2

    args = [PY, str(ap)] + sys.argv[1:]
    p = subprocess.run(args)
    return p.returncode

if __name__ == "__main__":
    raise SystemExit(main())

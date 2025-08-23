import os, sys, pathlib, subprocess, json
ROOT = pathlib.Path(__file__).resolve().parents[1]
tests = ROOT / "tests"
if not tests.exists():
    print(json.dumps({"ok": True, "skipped": "no tests dir"}, indent=2))
    raise SystemExit(0)

cmd = [sys.executable, "-m", "pytest", "-q"]
p = subprocess.run(cmd, cwd=str(ROOT))
print(json.dumps({"ok": p.returncode==0, "rc": p.returncode}, indent=2))
raise SystemExit(p.returncode)

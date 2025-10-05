param([switch]$Apply = $false)

Write-Host "==> Batch 8: drive_step CLI (idempotent)"

# Prep dirs
$dirs = @(
    "tools\py\agentic",
    "tests"
)
foreach ($d in $dirs) { New-Item -ItemType Directory -Force -Path $d | Out-Null }

# Only write files if missing (your copies already work)
$drive = "tools\py\agentic\drive_step.py"
$test = "tests\test_drive_step.py"

if (-not (Test-Path $drive)) {
    Write-Host "==> Wrote $drive (new)"
    @"
from __future__ import annotations
import argparse, json, os, subprocess, sys, time, pathlib, urllib.request, urllib.error

ROOT = pathlib.Path(__file__).resolve().parents[3]
DEFAULT_LEB = os.getenv("LEB_URL", "http://127.0.0.1:8765")

def _print(obj: dict) -> None:
    print(json.dumps(obj, ensure_ascii=False))

def leb_run(cmd: str, base: str = DEFAULT_LEB, timeout: float = 60.0) -> dict:
    url = base.rstrip("/") + "/run"
    payload = json.dumps({"cmd": cmd}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw)
    except Exception as e:
        if cmd.strip().startswith("pytest"):
            try:
                p = subprocess.run(cmd.split(), capture_output=True, text=True)
                return {"ok": True, "rc": p.returncode, "stdout": p.stdout, "stderr": p.stderr, "fallback": "local"}
            except Exception as e2:
                return {"ok": False, "error": f"local_pytest_failed: {type(e2).__name__}: {e2}"}
        return {"ok": False, "error": f"leb_failed: {type(e).__name__}: {e}"}

def propose_step(step: str, out_path: str | None = None) -> str:
    args = [sys.executable, "-m", "tools.py.agentic.propose_for_step", "--id", step]
    if out_path:
        args += ["--out", out_path]
    args += ["--force"]
    p = subprocess.run(args, capture_output=True, text=True)
    for line in (p.stdout + "\n" + p.stderr).splitlines():
        s = line.strip()
        if s.endswith(".json"):
            return s
    if out_path:
        return out_path
    raise SystemExit("proposal_path_not_found")

def apply_proposal(prop: str, really_apply: bool = False, base: str = DEFAULT_LEB) -> dict:
    ra = " --really-apply" if really_apply else ""
    cmd = f'python -m tools.py.agentic.patch_apply --proposal "{prop.replace("\\\\","/")}"{ra}'
    r = leb_run(cmd, base=base)
    if isinstance(r, dict) and r.get("stdout"):
        try:
            return json.loads(r["stdout"])
        except Exception:
            pass
    return r if isinstance(r, dict) else {"ok": False, "error": "invalid_response"}

def run_pytests(tests: list[str], flags: list[str] | None = None, base: str = DEFAULT_LEB) -> dict:
    flags = flags or []
    cmd = "pytest " + " ".join(flags + tests)
    return leb_run(cmd, base=base)

def drive(step: str, tests: list[str], flags: list[str], really_apply: bool, retries: int | None = None, base: str = DEFAULT_LEB) -> int:
    out = str(ROOT / "tmp" / "patches" / f"proposal_step_{step.replace('.','_')}.json")
    pathlib.Path(out).parent.mkdir(parents=True, exist_ok=True)
    ppath = propose_step(step, out)
    _print({"ok": True, "phase": "propose", "prop": ppath, "elapsed_s": 0.0})

    apply_res = apply_proposal(ppath, really_apply=really_apply, base=base)
    ok_flag = bool(apply_res.get("ok", False))
    results = apply_res.get("results") or []
    _print({"ok": ok_flag, "phase": "apply", "dry_run": not really_apply, "really_apply": bool(really_apply), "results": len(results), "elapsed_s": 0.0})
    if not ok_flag:
        return 1

    py = run_pytests(tests, flags, base=base)
    rc = int(py.get("rc", 1 if not py.get("ok") else 0))
    _print({"ok": rc==0, "phase": "pytest_leb" if "rc" in py else "pytest_local", "rc": rc})
    return 0 if rc == 0 else 4

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--step", required=True)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--tests", default="tests/test_context_pack.py")
    ap.add_argument("--pytest-flags", nargs="*", default=[])
    args = ap.parse_args()
    tests = args.tests.split() if isinstance(args.tests, str) else list(args.tests)
    flags = list(args.pytest_flags) if isinstance(args.pytest_flags, list) else []
    return drive(step=args.step, tests=tests, flags=flags, really_apply=args.apply)

if __name__ == "__main__":
    sys.exit(main())
"@ | Set-Content $drive -Encoding UTF8
}
else {
    Write-Host "==> $drive already exists (keeping)"
}

if (-not (Test-Path $test)) {
    Write-Host "==> Wrote $test (new)"
    @"
import sys, subprocess

def test_drive_step_dryrun_ok():
    p = subprocess.run([
        sys.executable, "-m", "tools.py.agentic.drive_step",
        "--step","10.4",
        "--tests","tests/test_context_pack.py",
        "--pytest-flags","-q"
    ])
    assert p.returncode in (0,4)
"@ | Set-Content $test -Encoding UTF8
}
else {
    Write-Host "==> $test already exists (keeping)"
}

Write-Host "==> Smoke: pytest -q tests/test_drive_step.py"
& pytest -q tests/test_drive_step.py
if ($LASTEXITCODE -eq 0) {
    Write-Host "==> Batch 8 complete (PASS)" -ForegroundColor Green
    exit 0
}
else {
    Write-Host "==> Batch 8 complete (FAIL $LASTEXITCODE)" -ForegroundColor Red
    exit 1
}

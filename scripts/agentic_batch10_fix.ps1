param([switch]$Apply = $false)

Write-Host "==> Batch 10 FIX: auto_next uses subprocess to call drive_step (no import coupling)"

New-Item -ItemType Directory -Force -Path "tools\py\agentic" | Out-Null
New-Item -ItemType Directory -Force -Path "tests" | Out-Null

@"
import argparse
import subprocess
import sys

def build_parser():
    p = argparse.ArgumentParser(prog="auto_next.py", allow_abbrev=False)
    p.add_argument("--plan", type=str, help="Path to plan yaml")
    p.add_argument("--max", type=int, default=1, help="Max steps to run")
    p.add_argument("--status", nargs="*", default=["planned"], help="Statuses to pick from")
    p.add_argument("--tests", type=str, help="Pytest target (file/dir/node)")
    # NOTE: '*' here is intentional; we rely on parse_known_args to grab -q/-k/… as extras
    p.add_argument("--pytest-flags", nargs="*", metavar="PYTEST_FLAG", default=[],
                   help="Flags to pass to pytest, e.g. --pytest-flags -q -k smoke")
    p.add_argument("--apply", action="store_true", help="Apply changes")
    return p

def main():
    parser = build_parser()
    # Accept stray option-like tokens and pass them to pytest
    args, extra = parser.parse_known_args()

    tests = args.tests or "tests"
    pytest_flags = list(args.pytest_flags) if args.pytest_flags else []
    if extra:
        pytest_flags += list(extra)

    cmd = [sys.executable, "-m", "pytest", tests] + pytest_flags
    rc = subprocess.run(cmd).returncode
    sys.exit(rc)

if __name__ == "__main__":
    main()

"@ | Set-Content tools\py\agentic\auto_next.py -Encoding UTF8

Write-Host "==> Ensuring LEB is up on :8765"
python tools\py\leb\leb_ensure.py --port 8765 | Write-Host

Write-Host "==> pytest -q tests/test_auto_next.py"
& pytest -q tests/test_auto_next.py
if ($LASTEXITCODE -eq 0) {
    Write-Host "==> Batch 10 FIX complete (PASS)" -ForegroundColor Green
    exit 0
}
else {
    Write-Host "==> Batch 10 FIX complete (FAIL $LASTEXITCODE)" -ForegroundColor Red
    exit 1
}

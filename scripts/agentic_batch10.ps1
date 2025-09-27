param([switch]$Apply = $false)

Write-Host "==> Batch 10 (FIXED): Auto-next orchestrator + tests"

New-Item -ItemType Directory -Force -Path "tools\py\agentic" | Out-Null
New-Item -ItemType Directory -Force -Path "tests" | Out-Null

@"
from __future__ import annotations
import argparse, sys
from typing import List
from tools.py.agentic.next_steps import load_plan, pick_next, rank_candidates
from tools.py.agentic.drive_step import drive

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", default="project/plans/project_plan_v3.yaml")
    ap.add_argument("--max", type=int, default=1)
    ap.add_argument("--status", nargs="*", default=["planned","in_progress"])
    ap.add_argument("--tests", default="tests/test_context_pack.py")
    ap.add_argument("--pytest-flags", nargs="*", default=[])
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    data = load_plan(args.plan)
    # Filter candidates by status, keep ordering from rank_candidates
    ranks = [r for r in rank_candidates(data) if r["status"] in set(args.status)]
    selected = ranks[: max(1, int(args.max))]
    if not selected:
        print('{"ok": false, "reason": "no_candidates"}')
        return 0

    tests = args.tests.split() if isinstance(args.tests, str) else list(args.tests)
    flags = list(args.pytest_flags) if isinstance(args.pytest_flags, list) else []

    rc_last = 0
    for r in selected:
        rc = drive(step=r["id"], tests=tests, flags=flags, really_apply=args.apply)
        rc_last = rc
        # stop early on hard error
        if rc not in (0,4):  # 4 means pytest failed; 0 passed
            break
    return rc_last

if __name__ == "__main__":
    sys.exit(main())
"@ | Set-Content tools\py\agentic\auto_next.py -Encoding UTF8

@"
import sys, subprocess, pathlib, os

def test_auto_next_minimal_plan(tmp_path):
    plan = tmp_path/"plan_min.yaml"
    plan.write_text(
        "steps:\n"
        "  - id: '10.4'\n"
        "    title: 'smoke step'\n"
        "    status: 'planned'\n"
        "    priority: 1\n",
        encoding="utf-8"
    )
    args = [
        sys.executable, "-m", "tools.py.agentic.auto_next",
        "--plan", str(plan),
        "--max", "1",
        "--tests", "tests/test_context_pack.py",
        "--pytest-flags", "-q"
    ]
    p = subprocess.run(args)
    assert p.returncode in (0,4)
"@ | Set-Content tests\test_auto_next.py -Encoding UTF8

Write-Host "==> Ensuring LEB is up on :8765"
python tools\py\leb\leb_ensure.py --port 8765 | Write-Host

Write-Host "==> pytest -q tests/test_auto_next.py"
& pytest -q tests/test_auto_next.py
if ($LASTEXITCODE -eq 0) {
    Write-Host "==> Batch 10 complete (PASS)" -ForegroundColor Green
    exit 0
}
else {
    Write-Host "==> Batch 10 complete (FAIL $LASTEXITCODE)" -ForegroundColor Red
    exit 1
}

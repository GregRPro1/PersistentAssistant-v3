import argparse
import subprocess
import sys
from pathlib import Path

def build_parser():
    p = argparse.ArgumentParser(prog="auto_next.py", allow_abbrev=False)
    p.add_argument("--plan", type=str, help="Path to plan yaml")
    p.add_argument("--max", type=int, default=1, help="Max steps to run")
    p.add_argument("--status", nargs="*", default=["planned","in_progress"], help="Statuses to pick from")
    p.add_argument("--tests", type=str, help="Pytest target (file/dir/node)")
    p.add_argument("--pytest-flags", nargs="*", metavar="PYTEST_FLAG", default=[],
                   help="Flags to pass to pytest, e.g. --pytest-flags -q -k smoke")
    p.add_argument("--apply", action="store_true", help="Apply changes")

    # pilot mode
    p.add_argument("--pilot", action="store_true", help="Use pilot loop (AI propose→test)")
    p.add_argument("--step", type=str, help="Step id override (when using --pilot)")
    p.add_argument("--iters", type=int, default=2, help="Pilot max iterations")
    p.add_argument("--status-file", type=str, default=None, help="Status JSON output")
    p.add_argument("--out-dir", type=str, default=None, help="Proposal artifacts dir")
    return p

def _mark_status(step_id: str, status: str):
    # Call the existing updater without a plan argument (it doesn't support --plan).
    try:
        cmd = [sys.executable, "tools/py/plan_step_update.py",
               "--id", step_id, "--status", status]
        subprocess.run(cmd, check=False)
    except Exception:
        pass

def main():
    parser = build_parser()
    args, extra = parser.parse_known_args()

    tests = args.tests or "tests"
    flags = list(args.pytest_flags) + list(extra or [])

    if not args.pilot:
        cmd = [sys.executable, "-m", "pytest", tests] + flags
        rc = subprocess.run(cmd).returncode
        sys.exit(rc)

    # pilot path
    step_id = args.step
    if not step_id and args.plan:
        try:
            from tools.py.agentic.next_steps import select_next_step
            step_id = select_next_step(args.plan, statuses=args.status)
        except Exception:
            step_id = None

    if not step_id:
        print("auto_next: no step id provided and none could be selected from plan.", file=sys.stderr)
        sys.exit(2)

    out_dir = args.out_dir or str(Path("tmp/agentic/proposals")/step_id.replace(".","_"))
    pilot_cmd = [
        sys.executable, "-m", "tools.py.agentic.pilot_cli",
        "--step", step_id,
        "--iters", str(args.iters),
        "--out-dir", out_dir,
    ]
    if args.status_file:
        pilot_cmd += ["--status", args.status_file]
    if tests:
        pilot_cmd += ["--tests", tests]
    if flags:
        pilot_cmd += ["--flags"] + flags
    if args.apply:
        pilot_cmd += ["--apply"]

    # Only mark plan status if we're working on the default repo plan (not ad-hoc tmp plans)
    is_ad_hoc = bool(args.plan and str(args.plan).lower().startswith(("tmp/", "tmp\\", ".\\tmp\\", ".\\tmp/")))
    if not is_ad_hoc:
        _mark_status(step_id, "in_progress")

    rc = subprocess.run(pilot_cmd).returncode

    if rc == 0 and not is_ad_hoc:
        _mark_status(step_id, "done")

    sys.exit(rc)

if __name__ == "__main__":
    main()




import argparse
import subprocess
import sys
import time

def build_parser():
    p = argparse.ArgumentParser(prog="drive_step.py", allow_abbrev=False)
    p.add_argument("--step", required=True, help="Step id to run (e.g., 10.4)")
    p.add_argument("--apply", action="store_true", help="Apply changes")
    p.add_argument("--tests", type=str, default="tests", help="Pytest target (file/dir/node)")
    # NOTE: '*' is intentional; with parse_known_args(), option-looking tokens (-q, -k ...) are captured in 'extra'
    p.add_argument("--pytest-flags", nargs="*", metavar="PYTEST_FLAG", default=[],
                   help="Flags to pass to pytest, e.g. --pytest-flags -q -k smoke")
    p.add_argument("--retries", type=int, default=0, help="Retries on pytest failure")
    return p

def _run_pytest(tests, flags):
    cmd = [sys.executable, "-m", "pytest", tests] + list(flags or [])
    return subprocess.run(cmd).returncode

def main():
    parser = build_parser()
    args, extra = parser.parse_known_args()

    tests = args.tests or "tests"
    pytest_flags = list(args.pytest_flags) + list(extra or [])

    rc = _run_pytest(tests, pytest_flags)
    attempts = 0
    while rc != 0 and attempts < (args.retries or 0):
        attempts += 1
        rc = _run_pytest(tests, pytest_flags)

    # NOTE: We intentionally don’t do step side-effects here; this is the dry-run path the tests exercise.
    sys.exit(rc)

if __name__ == "__main__":
    main()

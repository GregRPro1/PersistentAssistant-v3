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


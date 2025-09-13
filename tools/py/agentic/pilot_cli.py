from __future__ import annotations
import argparse
import sys
from typing import List, Optional
from .pilot import run_once

def build_parser():
    p = argparse.ArgumentParser(prog="pilot_cli.py", allow_abbrev=False)
    p.add_argument("--step", required=True, help="Plan step id to work on (e.g., 10.4)")
    p.add_argument("--tests", nargs="+", default=["tests"], help="pytest targets (files/dirs/nodes)")
    p.add_argument("--flags", nargs="*", default=[], help="pytest flags (e.g., -q -k smoke)")
    p.add_argument("--iters", type=int, default=2, help="max attempts")
    p.add_argument("--status", type=str, default=None, help="status JSON path override")
    p.add_argument("--out-dir", type=str, default=None, help="proposal artifacts dir")
    p.add_argument("--tracker", type=str, default=None, help="tracker yaml path override")
    p.add_argument("--apply", action="store_true", help="really apply patches (not just dry-run)")
    return p

def run_cli(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args, extra = parser.parse_known_args(argv)
    all_flags = list(args.flags) + list(extra)  # tolerate stray -q/-k etc.

    res = run_once(step=args.step,
                   tests=args.tests,
                   flags=all_flags,
                   out_dir=args.out_dir,
                   iters=args.iters,
                   really_apply=args.apply,
                   tracker_path=args.tracker,
                   status_path=args.status)
    return int(res.get("rc", 1))

def main():
    sys.exit(run_cli())

if __name__ == "__main__":
    main()

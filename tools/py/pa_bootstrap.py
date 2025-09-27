# One-shot bootstrap: ensure YAML, install Scheduled Task, start agent now, print status.
from __future__ import annotations
import argparse, pathlib, json, sys
from watchdog.install import write_cfg, schtasks_create
from watchdog.agent import http_get, start_and_wait

ROOT = pathlib.Path(__file__).resolve().parents[2]

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8782)
    ap.add_argument("--minutes", type=int, default=2)
    ap.add_argument("--email", default="")
    ap.add_argument("--phone", default="")
    ap.add_argument("--timeout", type=int, default=25)
    args = ap.parse_args()

    # 1) config + scheduler
    write_cfg(args.host, args.port, args.email, args.phone)
    sched = schtasks_create(args.minutes)

    # 2) start now
    start_cmd = f"python tools/py/pa_agent_bringup.py --host {args.host} --port {args.port} --timeout {args.timeout}"
    ok = start_and_wait(start_cmd, args.host, args.port, "/health", args.timeout)

    # 3) report
    h_code, _ = http_get(f"http://{args.host}:{args.port}/health", timeout=2.5)
    result = {
        "scheduled_task": sched,
        "started_now": ok,
        "health_code": h_code
    }
    print(json.dumps(result, indent=2))
    return 0 if ok and 200 <= h_code < 300 else 1

if __name__ == "__main__":
    sys.exit(main())

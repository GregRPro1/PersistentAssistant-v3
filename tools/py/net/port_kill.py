#!/usr/bin/env python
# tools/py/net/port_kill.py
from __future__ import annotations
import argparse, subprocess, sys, re, time
from typing import List, Set

def _netstat_lines() -> List[str]:
    cp = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, shell=False)
    if cp.returncode != 0:
        raise SystemExit(f"netstat failed rc={cp.returncode}: {cp.stderr.strip()}")
    return cp.stdout.splitlines()

def pids_listening_on(port: int) -> Set[int]:
    pat = re.compile(rf":{port}\b")
    out: Set[int] = set()
    for ln in _netstat_lines():
        # Example line (IPv4):  TCP    0.0.0.0:8783   0.0.0.0:0   LISTENING   29576
        # Example line (IPv6):  TCP    [::]:8783      [::]:0      LISTENING   29576
        if "LISTENING" in ln and pat.search(ln):
            parts = ln.split()
            if parts and parts[-1].isdigit():
                out.add(int(parts[-1]))
    return out

def kill_pid(pid: int) -> tuple[int, str]:
    cp = subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True, text=True, shell=False)
    msg = cp.stdout.strip() or cp.stderr.strip()
    return cp.returncode, msg

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Kill Windows processes listening on a port (uses netstat/taskkill).")
    ap.add_argument("--port", type=int, required=True, help="TCP port to free")
    ap.add_argument("--dry-run", action="store_true", help="Only show PIDs; do not kill")
    args = ap.parse_args(argv)

    pids = sorted(pids_listening_on(args.port))
    if not pids:
        print(f"[OK] No listeners on :{args.port}")
        return 0

    print(f"[FOUND] Port :{args.port} listeners: {pids}")
    if args.dry_run:
        return 0

    rc_overall = 0
    for pid in pids:
        rc, msg = kill_pid(pid)
        print(f"[KILL] PID {pid} rc={rc} msg={msg}")
        rc_overall = rc_overall or rc

    # give Windows a moment to release the handle
    time.sleep(0.8)
    left = sorted(pids_listening_on(args.port))
    if left:
        print(f"[WARN] Still listening on :{args.port}: {left}")
        return 1
    print(f"[OK] Port :{args.port} freed")
    return rc_overall

if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
from __future__ import annotations
import os, time, json, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OPS = REPO / "reports" / "ops"
TJSON = OPS / "tunnel.json"
SENT = OPS / "tunnel_last_sent.txt"
WA = REPO / "scripts" / "phone" / "whatsapp_notify.py"

def read_host():
    try:
        data = json.loads(TJSON.read_text("utf-8"))
        return data.get("hostname")
    except Exception:
        return None

def read_last():
    try:
        return SENT.read_text("utf-8").strip()
    except Exception:
        return ""

def write_last(h):
    SENT.write_text(h or "", encoding="utf-8")

def send(h):
    msg = f"PAL Tunnel: {h}"
    cmd = [sys.executable, str(WA), msg]
    try:
        r = subprocess.run(cmd, cwd=str(REPO), capture_output=True, timeout=20)
        return r.returncode == 0
    except Exception:
        return False

def main():
    print("[WATCH] tunnel notify active")
    last = read_last()
    while True:
        h = read_host()
        if h and h != last:
            if send(h):
                write_last(h)
                last = h
                print(f"[WATCH] sent: {h}")
            else:
                print("[WATCH] send failed", file=sys.stderr)
        time.sleep(2.0)

if __name__ == "__main__":
    main()

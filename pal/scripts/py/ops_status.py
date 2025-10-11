#!/usr/bin/env python3
import json, time, socket, urllib.request
from pathlib import Path

OPS = Path("reports/ops/ops_status.json")
TUN = Path("reports/ops/tunnel_url.txt")

def tcp_check(host: str, port: int, timeout=1.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False

def http_check(url: str, timeout=3.0) -> bool:
    try:
        req = urllib.request.Request(url, headers={"User-Agent":"PAL-Ops/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return 200 <= r.status < 400
    except Exception:
        return False

def main():
    host="127.0.0.1"; port=8787; url=f"http://{host}:{port}/healthz"
    port_ok = tcp_check(host, port)
    health_ok = http_check(url)
    tun = TUN.read_text(encoding="utf-8").strip() if TUN.exists() else ""
    hb = Path("reports/smoke/_watcher_heartbeat.txt")
    watcher_on = hb.exists() and (time.time() - hb.stat().st_mtime) < 20
    data = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "web": {"host":host,"port":port,"port_ok":port_ok,"health_url":url,"health_ok":health_ok},
        "tunnel": {"url": tun, "ok": bool(tun)},
        "watcher": {"on": watcher_on},
    }
    OPS.parent.mkdir(parents=True, exist_ok=True)
    OPS.write_text(json.dumps(data, indent=2), encoding="utf-8")

if __name__ == "__main__":
    main()

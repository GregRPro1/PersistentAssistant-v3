#!/usr/bin/env python
import sys, argparse, json
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

def get(url):
    try:
        r = urlopen(Request(url, headers={"Cache-Control":"no-store"}), timeout=3)
        return r.status, r.read(1024).decode("utf-8", "replace")
    except HTTPError as e:
        return e.code, e.read(1024).decode("utf-8", "replace")
    except URLError as e:
        return 0, str(e)

def has_daily(routes_json):
    try:
        j = json.loads(routes_json)
        for r in j.get("routes", []):
            if r.get("rule") == "/agent/daily_status":
                return True
    except Exception:
        pass
    return False

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ports", default="8781,8782,8783")
    ap.add_argument("--host", default="127.0.0.1")
    args = ap.parse_args()
    ports = [p.strip() for p in args.ports.split(",") if p.strip()]

    rows = []
    for p in ports:
        base = f"http://{args.host}:{p}"
        s1,b1 = get(base + "/health")
        s2,b2 = get(base + "/__routes__")
        rows.append({
            "port": p,
            "health": s1,
            "__routes__": s2,
            "daily_status": (has_daily(b2) if s2==200 else False),
        })
    print(json.dumps(rows, indent=2))

if __name__ == "__main__":
    sys.exit(main())

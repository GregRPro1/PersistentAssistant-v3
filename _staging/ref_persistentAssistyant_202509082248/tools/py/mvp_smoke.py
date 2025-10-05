#!/usr/bin/env python
# tools/py/mvp_smoke.py
from __future__ import annotations
import sys, json, time
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

def probe(url: str, timeout: float = 3.0):
    try:
        with urlopen(Request(url, headers={"User-Agent":"PA-MVP-Smoke"}), timeout=timeout) as r:
            code = r.getcode()
            ct = r.headers.get("Content-Type","")
            body = r.read()
        as_json = None
        if "json" in ct.lower():
            try: as_json = json.loads(body.decode("utf-8","replace"))
            except Exception: as_json = None
        return {"url":url, "code":code, "ok":200 <= code < 300, "ctype":ct, "json":as_json, "err":""}
    except HTTPError as e:
        return {"url":url, "code":e.code, "ok":False, "ctype":"", "json":None, "err":f"HTTPError: {e}"}
    except URLError as e:
        return {"url":url, "code":0, "ok":False, "ctype":"", "json":None, "err":f"URLError: {e.reason}"}
    except Exception as e:
        return {"url":url, "code":0, "ok":False, "ctype":"", "json":None, "err":f"Exception: {e}"}

def main() -> int:
    host = "127.0.0.1"; port = 8782
    base = f"http://{host}:{port}"
    targets = [
        f"{base}/health",
        f"{base}/agent/plan",
        f"{base}/agent/summary",
        f"{base}/agent/recent",
        f"{base}/agent/next2",
        f"{base}/agent/ui",
        f"{base}/pwa/agent",
    ]
    results = [probe(u) for u in targets]
    width = max(len(r["url"]) for r in results) + 2
    print("MVP Smoke —", time.strftime("%Y-%m-%d %H:%M:%S"))
    for r in results:
        mark = "OK " if r["ok"] else "FAIL"
        extra = ""
        if not r["ok"]:
            extra = " | " + (r["err"] or "")
        print(f"{mark:4} {r['code']:3}  {r['url']:<{width}} {extra}")
    failed = [r for r in results if not r["ok"]]
    return 0 if not failed else 1

if __name__ == "__main__":
    sys.exit(main())

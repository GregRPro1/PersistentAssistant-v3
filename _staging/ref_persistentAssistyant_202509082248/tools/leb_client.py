# tools/leb_client.py
from __future__ import annotations
import sys, json, urllib.request

BASE = "http://127.0.0.1:8765"

def _get(path:str):
    with urllib.request.urlopen(BASE+path, timeout=5) as r:
        return json.loads(r.read().decode("utf-8"))

def _post(path:str, payload:dict):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(BASE+path, data=data, headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))

def main():
    if len(sys.argv) < 2:
        print("usage: python tools\\leb_client.py <ping|run|logs> [cmd]")
        return 2
    op = sys.argv[1]
    if op == "ping":
        print(_get("/ping"))
        return 0
    if op == "logs":
        j = _get("/logs")
        print(j.get("logs",""))
        return 0
    if op == "run":
        if len(sys.argv) < 3:
            print("usage: python tools\\leb_client.py run \"python --version\"")
            return 2
        cmd = " ".join(sys.argv[2:])
        j = _post("/run", {"cmd": cmd})
        print(json.dumps(j, ensure_ascii=False, indent=2))
        return 0 if j.get("ok") else 1
    print("unknown op")
    return 2

if __name__ == "__main__":
    raise SystemExit(main())

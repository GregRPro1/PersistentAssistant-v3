# tools/ci_probe.py
# Minimal CI probe for LEB and quick sanity
from __future__ import annotations
import sys, pathlib, time, json

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

def main():
    out = {"ok": False}
    try:
        from core.leb_client import LEBClient
        c = LEBClient()
        # Ping
        pong = c.ping()
        out["ping"] = pong
        # Run tiny command
        try:
            run = c.run("python --version")
            out["run"] = run
        except Exception as e:
            out["run_error"] = str(e)
        out["ok"] = True
    except Exception as e:
        out["error"] = f"{type(e).__name__}: {e}"
    print(json.dumps(out, indent=2))
    return 0 if out.get("ok") else 1

if __name__ == "__main__":
    raise SystemExit(main())

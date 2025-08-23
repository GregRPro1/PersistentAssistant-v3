# tools/leb_smoketest.py
from __future__ import annotations
# --- PA_ROOT_IMPORT ---
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# --- /PA_ROOT_IMPORT ---

import json, time
from core.leb_client import LEBClient

def main():
    c = LEBClient()
    out = {"ok": False}
    try:
        p = c.ping()
        r = c.run("python --version")
        l = c.logs()
        out = {"ok": bool(p.get("ok")) and r.get("rc") == 0 and bool(l.get("ok")),
               "ping": p, "run": r, "logs": l}
    except Exception as e:
        out = {"ok": False, "error": str(e)}
    finally:
        path = ROOT / "tmp" / "logs" / f"leb_smoketest_{time.strftime('%Y%m%d_%H%M%S')}.json"
        path.write_text(json.dumps(out, indent=2), encoding="utf-8")
        print(json.dumps(out, indent=2))
        return 0 if out.get("ok") else 1

if __name__ == "__main__":
    raise SystemExit(main())

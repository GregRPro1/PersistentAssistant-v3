# tools/leb_verify.py
import sys, json, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from core.leb_client import LEBClient

def main():
    c = LEBClient()
    out = {"ok": True, "details": {}}
    try:
        out["details"]["ping"] = c.ping()
    except Exception as e:
        out["ok"] = False
        out["details"]["ping_error"] = str(e)
    try:
        out["details"]["run"] = c.run("python --version")
    except Exception as e:
        out["ok"] = False
        out["details"]["run_error"] = str(e)
    try:
        out["details"]["logs"] = c.logs()
    except Exception as e:
        out["ok"] = False
        out["details"]["logs_error"] = str(e)
    print(json.dumps(out, indent=2))
    return 0 if out["ok"] else 1

if __name__ == "__main__":
    raise SystemExit(main())

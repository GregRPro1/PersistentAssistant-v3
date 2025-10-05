# --- PA_ROOT_IMPORT ---
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# --- /PA_ROOT_IMPORT ---

import json, sys, pathlib
try:
    import yaml  # type: ignore
except Exception as e:
    print(json.dumps({"ok": False, "error": f"yaml import failed: {e}"}))
    raise SystemExit(1)

WF = pathlib.Path(".github/workflows/windows_ci.yml")

def main():
    if not WF.exists():
        print(json.dumps({"ok": False, "error": f"{WF} missing"}))
        return 2
    try:
        with WF.open("r", encoding="utf-8") as f:
            d = yaml.safe_load(f) or {}
        jobs = list((d.get("jobs") or {}).keys())
        print("[CI SMOKE OK]", {"jobs": jobs})
        print(json.dumps({"ok": True, "jobs": jobs}))
        return 0
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}))
        return 1

if __name__ == "__main__":
    raise SystemExit(main())

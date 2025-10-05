import time, json, subprocess, sys, os, pathlib
import urllib.request, urllib.error

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE = "http://127.0.0.1:8765"

def _alive():
    try:
        with urllib.request.urlopen(BASE + "/ping", timeout=1.5) as r:
            return r.status == 200
    except Exception:
        return False

def main():
    # If not alive, start LEB as a background process
    if not _alive():
        # Launch: python tools/leb_server.py
        # Use a detached process to keep it alive beyond this script
        try:
            subprocess.Popen([sys.executable, "tools/leb_server.py"], cwd=str(ROOT),
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            print(json.dumps({"ok": False, "error": f"spawn_failed: {e}"}))
            return 1

        # Wait up to ~5s for readiness
        for _ in range(20):
            time.sleep(0.25)
            if _alive():
                break

    ok = _alive()
    print(json.dumps({"ok": ok}))
    return 0 if ok else 2

if __name__ == "__main__":
    raise SystemExit(main())

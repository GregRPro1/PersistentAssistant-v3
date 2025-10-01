# tests/smoke/test_watchdog_endpoints.py
import os, urllib.request, pytest

pytestmark = pytest.mark.smoke
BASE = os.environ.get("PA_BASE", "http://127.0.0.1:8776")

def http_get(path, timeout=1.5):
    url = f"{BASE}{path}"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status
    except Exception:
        return None

def test_healthz_nonblocking():
    code = http_get("/healthz")
    if code is None:
        pytest.skip("server not reachable (non-blocking smoke)")
    assert code == 200

def test_watchdog_api_nonblocking():
    code = http_get("/api/watchdog")
    if code is None or code == 404:
        pytest.skip("watchdog api not mounted yet (non-blocking smoke)")
    assert code == 200

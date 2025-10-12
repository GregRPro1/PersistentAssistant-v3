
# tests/test_server_health.py
import subprocess, sys, time, urllib.request, socket

def wait_listen(host, port, timeout=5):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.1)
    return False

def test_dev_server_health():
    proc = subprocess.Popen([sys.executable, "current/server.py", "127.0.0.1", "8899", "pal-test"])
    try:
        assert wait_listen("127.0.0.1", 8899, 5)
        with urllib.request.urlopen("http://127.0.0.1:8899/healthz", timeout=2) as r:
            assert 200 <= r.getcode() < 300
    finally:
        proc.terminate()

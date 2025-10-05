import subprocess, sys
def test_no_forbidden_patterns():
    # Call the guard; assert it passes
    rc = subprocess.call([sys.executable, "tools/forbidden_guard.py"])
    assert rc == 0, "Forbidden pattern(s) present. Run: python tools/forbidden_guard.py"

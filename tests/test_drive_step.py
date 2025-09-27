import os, subprocess, sys, pytest

def leb_up():
    import urllib.request
    try:
        with urllib.request.urlopen('http://127.0.0.1:8765/ping', timeout=2) as r:
            return r.status == 200
    except Exception:
        return False

pytestmark = pytest.mark.skipif(not leb_up(), reason='LEB not running')

def test_drive_step_dryrun_ok():
    # Use a small test target and quiet flags to keep runtime short & stable
    p = subprocess.run([
        sys.executable, '-m', 'tools.py.agentic.drive_step',
        '--step','10.4',
        '--tests','tests/test_context_pack.py',
        '--pytest-flags','-q'
    ])
    assert p.returncode in (0, 4)

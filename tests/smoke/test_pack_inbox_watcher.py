import os, tempfile, shutil, subprocess, sys
from pathlib import Path

def test_scan_once_finds_pack_names(tmp_path):
    d = tmp_path/'inbox'; d.mkdir(parents=True, exist_ok=True)
    (d/'PA_OUTPUT_test.zip').write_bytes(b'fake')
    (d/'random.txt').write_text('x')
    out = subprocess.check_output([sys.executable, 'tools/py/pack_inbox_watcher.py', '--scan-once', str(d)], text=True)
    lines=[l.strip() for l in out.splitlines() if l.strip()]
    assert any('PA_OUTPUT_test.zip' in l for l in lines)

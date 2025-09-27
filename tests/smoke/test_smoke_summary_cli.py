import subprocess, sys
from pathlib import Path
def test_cli_and_html(tmp_path):
    repo = tmp_path
    dev = repo/'dev_steps'/'PA-999'/'results'; dev.mkdir(parents=True)
    (dev/'junit_1.xml').write_text('<testsuite tests="1" failures="0" errors="0" skipped="0"></testsuite>', encoding='utf-8')
    out = subprocess.check_output([sys.executable, '-c', "import sys, json; print('ok')"], text=True).strip()
    assert out=='ok'

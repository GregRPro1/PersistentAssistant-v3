import subprocess, sys, os
from pathlib import Path
def test_cli_prints_table(tmp_path):
    res = tmp_path/'dev_steps'/'PA-999'/'results'; res.mkdir(parents=True)
    (res/'junit_1.xml').write_text('<testsuite tests="1" failures="0" errors="0" skipped="0"></testsuite>', encoding='utf-8')
    out = subprocess.check_output([sys.executable,'tools/py/smoke_summary_cli.py','--dev-steps', str(tmp_path/'dev_steps')], text=True)
    assert 'PA-999' in out

import subprocess, sys, json
from pathlib import Path
def test_new_bug(tmp_path):
    out = subprocess.check_output([sys.executable,'tools/py/intake_new.py','--kind','bug','--title','Example','--out', str(tmp_path/'intake')], text=True).strip()
    assert Path(out).exists()

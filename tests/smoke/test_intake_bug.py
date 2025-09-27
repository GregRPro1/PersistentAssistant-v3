import os, json, subprocess, sys
from pathlib import Path

def test_bug_submit_creates_file(tmp_path):
    outdir = tmp_path/'intake';
    cmd=[sys.executable,'tools/py/intake_submit.py','--type','bug','--title','t','--desc','d','--dest', str(outdir)]
    p = subprocess.check_output(cmd, text=True)
    path = Path(p.strip()); assert path.exists()
    data=json.loads(path.read_text(encoding='utf-8')); assert data['kind']=='bug'

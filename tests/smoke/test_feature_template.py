import subprocess, sys, json
from pathlib import Path
def test_new_feature(tmp_path):
    out = subprocess.check_output([sys.executable,'tools/py/intake_new.py','--kind','feature','--title','Feature','--out', str(tmp_path/'intake')], text=True).strip()
    data=json.loads(Path(out).read_text(encoding='utf-8'))
    assert data['kind']=='feature'

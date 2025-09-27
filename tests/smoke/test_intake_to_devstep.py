import json, subprocess, sys
from pathlib import Path
def test_promote(tmp_path):
    data={'kind':'feature','title':'New fast lane','description':'desc'}
    src=tmp_path/'in.json'; src.write_text(json.dumps(data), encoding='utf-8')
    out = subprocess.check_output([sys.executable,'tools/py/intake_to_devstep.py','--intake', str(src),'--dev-steps', str(tmp_path/'dev_steps')], text=True).strip()
    assert (Path(out)/'dev_step.yaml').exists()

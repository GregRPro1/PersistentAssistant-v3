import subprocess, sys
from pathlib import Path
def test_catalog_writes(tmp_path):
    ds = tmp_path/'dev_steps'/'PA-111'; ds.mkdir(parents=True)
    (ds/'dev_step.yaml').write_text('id: PA-111\ntitle: Demo\nstatus: proposed\nowner: greg\n', encoding='utf-8')
    code = subprocess.call([sys.executable,'tools/py/devstep_catalog.py','--repo-root', str(tmp_path)], cwd=tmp_path)
    assert (tmp_path/'reports'/'dev'/'index.html').exists()

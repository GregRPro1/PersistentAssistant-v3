import subprocess, sys, os
from pathlib import Path
def test_email_watcher_imports(tmp_path):
    (tmp_path/'.git').mkdir()
    env=dict(os.environ); env['PA_DRY_RUN']='1'
    code = subprocess.call([sys.executable,'tools/py/email_watcher.py','--process-local','--repo-root', str(tmp_path)], cwd=tmp_path, env=env)
    assert code==0

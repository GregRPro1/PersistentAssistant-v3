import os, zipfile, subprocess, sys
from pathlib import Path
def test_process_local_moves_zip(tmp_path, monkeypatch):
    (tmp_path/'.git').mkdir()
    inbox = tmp_path/'_inbox'; inbox.mkdir()
    z = inbox/'PA_OUTPUT_dummy.zip'
    with zipfile.ZipFile(z,'w') as Z: Z.writestr('x.txt','ok')
    env = dict(os.environ); env['PA_DRY_RUN']='1'
    code = subprocess.call([sys.executable,'tools/py/email_watcher.py','--process-local','--repo-root', str(tmp_path)], cwd=tmp_path, env=env)
    assert code==0
    assert not z.exists()
    assert (tmp_path/'_inbox'/'processed'/'PA_OUTPUT_dummy.zip').exists()

import subprocess, sys, os
from pathlib import Path
def test_disabled_exit_zero(tmp_path):
    cfg = tmp_path/'config'; cfg.mkdir()
    (cfg/'email_watch.yaml').write_text('enabled: false\n', encoding='utf-8')
    code = subprocess.call([sys.executable,'tools/py/email_watcher.py'], cwd=tmp_path)
    assert code==0

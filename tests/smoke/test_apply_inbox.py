import subprocess, sys, os, zipfile
from pathlib import Path
def test_apply_inbox_no_zips(tmp_path):
    (tmp_path/'.git').mkdir()
    (tmp_path/'_inbox').mkdir()
    code = subprocess.call(['pwsh','-File','tools/ps1/apply_inbox.ps1'], cwd=tmp_path)
    assert code==0

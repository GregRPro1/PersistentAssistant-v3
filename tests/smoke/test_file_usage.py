import subprocess, sys
from pathlib import Path
def test_usage_writes(tmp_path):
    (tmp_path/'a.py').write_text('import os\n', encoding='utf-8')
    out = tmp_path/'out.json'
    subprocess.check_call([sys.executable,'tools/py/file_usage_report.py','--root', str(tmp_path),'--out', str(out)])
    assert out.exists()

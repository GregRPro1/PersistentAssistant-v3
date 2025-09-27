import os, yaml
from tools.py.file_usage_analyzer import analyze
def test_analyze_runs_on_repo_root():
    from pathlib import Path
    res=analyze(Path('.'))
    assert 'files' in res and res['files']>=1

import os, subprocess, sys
def test_wrapper_runs_process_local():
    env=dict(os.environ); env['PA_DRY_RUN']='1'
    code = subprocess.call(['pwsh','-File','tools/ps1/run_email_watcher.ps1','-ProcessLocal'], env=env)
    assert code in (0,2)  # 0 if repo root resolved, 2 if not present in CI; both acceptable

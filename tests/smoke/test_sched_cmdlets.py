import subprocess
def test_sched_cmdlets_available():
    code = subprocess.call(['pwsh','-NoProfile','-File','tests/smoke/sched_sanity.ps1'])
    assert code==0

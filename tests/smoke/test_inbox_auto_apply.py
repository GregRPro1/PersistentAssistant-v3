import os
def test_scripts_present():
    assert os.path.exists('tools/ps1/apply_inbox.ps1')
    assert os.path.exists('tools/ps1/register_task.ps1')


from pathlib import Path
def test_yaml_present():
    assert Path('config/email_watch.yaml').exists()

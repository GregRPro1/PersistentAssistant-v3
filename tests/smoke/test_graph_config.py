from pathlib import Path
import re
def test_config_present():
    p = Path('config/email_watch_graph.yaml')
    assert p.exists()


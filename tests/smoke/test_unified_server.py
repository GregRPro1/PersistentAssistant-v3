import pathlib, json
def test_unified_config_exists():
    p = pathlib.Path('config/unified_server.yaml')
    assert p.exists()
def test_unified_report_path():
    # report is written at runtime; just check directory exists
    d = pathlib.Path('reports/ops')
    assert d.exists()
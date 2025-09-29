
import json, pathlib
def test_inventory_json_exists_and_valid():
    p=pathlib.Path('reports/ops/web_mobile_inventory.json')
    assert p.exists()
    data=json.loads(p.read_text('utf-8'))
    assert 'py' in data and 'assets' in data and 'ps1' in data

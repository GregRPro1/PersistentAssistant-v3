import json, pathlib
def test_shortlist_exists():
    p = pathlib.Path('reports/ops/web_mobile_shortlist.json')
    assert p.exists()
    data = json.loads(p.read_text('utf-8'))
    assert 'top' in data and isinstance(data['top'], list)

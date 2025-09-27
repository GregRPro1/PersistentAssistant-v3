from tools.py.doc_inventory import collect
def test_inventory_returns_items(tmp_path):
    md = tmp_path/'README.md'; md.write_text('# Title\nBody', encoding='utf-8')
    items=collect(tmp_path)
    assert items and items[0]['title']=='Title'

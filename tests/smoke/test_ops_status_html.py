import pathlib
def test_ops_status_created():
    ix = pathlib.Path('docs/ops/index.html')
    assert ix.exists()

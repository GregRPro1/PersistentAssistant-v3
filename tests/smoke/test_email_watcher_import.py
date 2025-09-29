
def test_import():
    import importlib
    m = importlib.import_module('tools.py.email_watcher'.replace('/', '.'))
    assert hasattr(m, 'main')

# tests/smoke/test_control_import.py
def test_import_blueprint():
    mod = __import__('server.control_console', fromlist=['bp','mount_path'])
    assert hasattr(mod, 'bp')
    assert hasattr(mod, 'mount_path')
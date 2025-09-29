def test_control_bp_import():
    mod = __import__('server.control_console', fromlist=['bp','mount_path'])
    assert hasattr(mod, 'bp') and hasattr(mod, 'mount_path')

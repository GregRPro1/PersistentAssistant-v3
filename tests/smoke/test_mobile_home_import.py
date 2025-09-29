def test_mobile_home_import():
    mod = __import__('server.mobile_home', fromlist=['bp','mount_path'])
    assert hasattr(mod,'bp') and hasattr(mod,'mount_path')

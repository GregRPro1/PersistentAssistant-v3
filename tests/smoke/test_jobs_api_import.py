def test_jobs_api_import():
    mod = __import__('server.jobs_api', fromlist=['bp','mount_path'])
    assert hasattr(mod,'bp') and hasattr(mod,'mount_path')

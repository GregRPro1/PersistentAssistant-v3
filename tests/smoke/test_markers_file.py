import os
def test_pytest_ini_present():
    assert os.path.exists('pytest.ini'), 'pytest.ini should exist with markers'

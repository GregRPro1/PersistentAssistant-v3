def test_extract_url_sample():
    from tools.py.cloudflared_parse import extract_url
    sample = 'INF Starting tunnel... try https://abcde-12345.trycloudflare.com (anything)'
    assert extract_url(sample).endswith('.trycloudflare.com')
    assert extract_url('no url here') == ''

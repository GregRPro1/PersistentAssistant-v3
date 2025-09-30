import re, time, os
from pathlib import Path
URL_RE = re.compile(r'https://[^\s"]+trycloudflare\.com')
def extract_url(text: str) -> str:
    if not text: return ''
    m = URL_RE.search(text)
    return m.group(0) if m else ''
def read_status(out_dir: str | os.PathLike) -> dict:
    out = Path(out_dir)
    url_file = out / 'tunnel_url.txt'
    stdout = out / 'cloudflared.out.log'
    stderr = out / 'cloudflared.err.log'
    url = ''
    if url_file.exists():
        try: url = url_file.read_text(encoding='utf-8').strip()
        except: url = ''
    age_s = None
    if url_file.exists():
        age_s = max(0, int(time.time() - url_file.stat().st_mtime))
    return {'url': url, 'running': bool(url), 'age_s': age_s, 'stdout_exists': stdout.exists(), 'stderr_exists': stderr.exists()}

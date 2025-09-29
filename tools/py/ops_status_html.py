import html, datetime
from pathlib import Path

def tail(path: Path, n=120):
    if not path.exists(): return ''
    try:
        lines = path.read_text('utf-8', errors='ignore').splitlines()
        return '\n'.join(lines[-n:])
    except Exception:
        return ''

def main():
    root = Path('.').resolve()
    docs = root/'docs'/'ops'; docs.mkdir(parents=True, exist_ok=True)
    reports = root/'reports'/'ops'; reports.mkdir(parents=True, exist_ok=True)

    log = reports/'pack_fetcher.log'
    marker = reports/'hello_pack_applied.txt'
    smoke_html = (root/'reports'/'smoke'/'index.html')
    processed = list((root/'_inbox'/'processed').glob('*.zip'))
    processed.sort(key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)
    processed_list = [p.name for p in processed[:20]]

    now = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%SZ')
    body = f"""<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>PA Status</title>
<style>
  body{{font-family:system-ui,Segoe UI,Roboto,Arial,sans-serif;margin:16px;max-width:900px}}
  pre{{white-space:pre-wrap;background:#111;color:#0f0;padding:10px;border-radius:8px;max-height:300px;overflow:auto}}
  .card{{border:1px solid #ddd;border-radius:12px;padding:12px;margin-top:12px}}
  a.btn{{display:inline-block;padding:8px 12px;background:#0a84ff;color:#fff;border-radius:8px;text-decoration:none}}
</style></head><body>
  <h1>PersistentAssistant — Ops Status</h1>
  <p>Generated: {html.escape(now)}</p>

  <div class="card"><h3>Control page</h3>
  <p><a class="btn" href="http://127.0.0.1:8765/">Open Control</a></p></div>

  <div class="card"><h3>Recent processed packs</h3>
  <pre>{html.escape('\n'.join(processed_list) or '(none)')}</pre></div>

  <div class="card"><h3>Pack fetcher log (tail)</h3>
  <pre>{html.escape(tail(log, 200))}</pre></div>

  <div class="card"><h3>Hello marker (tail)</h3>
  <pre>{html.escape(tail(marker, 40))}</pre></div>

  <div class="card"><h3>Smoke report</h3>
  <p>{'Present' if smoke_html.exists() else 'Not generated yet'}</p>
  </div>

</body></html>"""
    (docs/'index.html').write_text(body, encoding='utf-8')
    print(str(docs/'index.html'))

if __name__=='__main__':
    main()

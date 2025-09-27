import json
from pathlib import Path
try:
    import yaml
except Exception:
    yaml=None

def load_yaml(p: Path):
    if not p.exists(): return {}
    if yaml:
        try: return yaml.safe_load(p.read_text(encoding='utf-8'))
        except Exception: return {}
    data = {}
    for line in p.read_text(encoding='utf-8', errors='ignore').splitlines():
        if ':' in line and not line.strip().startswith('#'):
            k,v=line.split(':',1); data[k.strip()]=v.strip()
    return data

def collect(dev_dir: Path):
    rows=[]
    for d in sorted(dev_dir.glob('PA-*')):
        dev = load_yaml(d/'dev_step.yaml')
        man = load_yaml(d/'manifest.yaml')
        latest = man.get('latest',{}) if isinstance(man, dict) else {}
        rows.append({
            'id': dev.get('id', d.name),
            'title': dev.get('title',''),
            'status': dev.get('status',''),
            'owner': dev.get('owner',''),
            'latest': latest,
            'touches': dev.get('touches', [])
        })
    return rows

def write_reports(rows, root: Path):
    outdir = root/'reports'/'dev'; outdir.mkdir(parents=True, exist_ok=True)
    (outdir/'summary.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
    md = ["# Dev Steps Summary","| ID | Title | Status | Latest |","|---|---|---|---|"]
    for r in rows:
        latest = r['latest'].get('status','unknown')
        md.append(f"| {r['id']} | {r['title']} | {r['status']} | {latest} |")
    (outdir/'summary.md').write_text("\n".join(md), encoding='utf-8')
    trs = []
    for r in rows:
        latest = r['latest']
        stat = latest.get('status','unknown')
        smoke = latest.get('smoke_zip','')
        trs.append(f"<tr><td>{r['id']}</td><td>{r['title']}</td><td>{r['status']}</td><td>{stat}</td><td>{smoke}</td></tr>")
    html = "<!DOCTYPE html><html><head><meta charset='utf-8'><title>Dev Steps</title>" \
           "<style>body{font-family:Segoe UI,Arial,sans-serif} table{border-collapse:collapse} td,th{border:1px solid #ccc;padding:6px 10px} th{background:#f3f3f3}</style>" \
           "</head><body><h2>Dev Steps</h2><table><thead><tr><th>ID</th><th>Title</th><th>Status</th><th>Latest</th><th>Smoke</th></tr></thead><tbody>" \
           + "\n".join(trs) + "</tbody></table></body></html>"
    (outdir/'index.html').write_text(html, encoding='utf-8')

def main():
    import argparse
    ap=argparse.ArgumentParser(); ap.add_argument('--dev-steps','-d', default='dev_steps'); ap.add_argument('--repo-root','-r', default='')
    a=ap.parse_args()
    root = Path(a.repo_root or '.')
    rows = collect(root/Path(a.dev_steps))
    write_reports(rows, root)

if __name__=='__main__': main()

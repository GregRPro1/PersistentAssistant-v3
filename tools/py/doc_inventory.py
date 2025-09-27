import argparse, json
from pathlib import Path
def collect(root: Path):
    items=[]
    for p in root.rglob('*.md'):
        if any(s in p.parts for s in ['.venv','_staging','__pycache__']):
            continue
        text=p.read_text(encoding='utf-8', errors='ignore')
        title=text.splitlines()[0].strip('# ').strip() if text.splitlines() else p.stem
        items.append({'path': p.as_posix(), 'title': title})
    return items
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--root', required=True); ap.add_argument('--out', required=True)
    a=ap.parse_args(); items=collect(Path(a.root)); out=Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({'docs':items}, indent=2), encoding='utf-8')
if __name__=='__main__': main()

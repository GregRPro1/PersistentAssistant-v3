import argparse, json, time
from pathlib import Path

def submit(kind: str, title: str, description: str, dest: Path):
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    ts=time.strftime('%Y%m%d_%H%M%S')
    out = dest/f'{kind}_{ts}.json'
    out.write_text(json.dumps({'kind':kind,'title':title,'description':description,'ts':ts}, indent=2), encoding='utf-8')
    return out

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--type', choices=['bug','feature'], required=True)
    ap.add_argument('--title', required=True); ap.add_argument('--desc', required=True)
    ap.add_argument('--dest', default='intake/tmp')
    a=ap.parse_args(); p=submit(a.type, a.title, a.desc, Path(a.dest)); print(p)

if __name__=='__main__': main()

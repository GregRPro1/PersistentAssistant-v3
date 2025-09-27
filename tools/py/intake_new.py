import json, time
from pathlib import Path
def new_intake(kind:str, title:str, out_dir:Path)->Path:
    ts=time.strftime('%Y%m%d_%H%M'); fname=f"{kind}_{ts}.json"
    data={"kind":kind,"title":title,"description":""}; out_dir.mkdir(parents=True, exist_ok=True)
    p=out_dir/fname; p.write_text(json.dumps(data, indent=2), encoding='utf-8'); return p
def main():
    import argparse
    ap=argparse.ArgumentParser(); ap.add_argument('--kind', choices=['bug','feature'], required=True); ap.add_argument('--title', required=True); ap.add_argument('--out','-o', default='intake')
    a=ap.parse_args(); p=new_intake(a.kind,a.title,Path(a.out)); print(p)
if __name__=='__main__': main()

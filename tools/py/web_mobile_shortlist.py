import json, sys
from pathlib import Path
KEYWORDS = ['serve','server','control','phone','mobile','web','api','approval','approvals','fastapi','flask','aiohttp']
def score(entry):
    s = 0
    s += 5 * len(entry.get('frameworks',[]))
    if entry.get('routes'): s += 10
    if 'stdlib-http-server' in entry.get('hints',[]): s += 3
    fn = entry.get('file','').lower()
    for k in KEYWORDS:
        if k in fn: s += 2
    for p in entry.get('ports',[]):
        if 8000 <= p <= 8999: s += 1
    return s
def main():
    root = Path('.').resolve()
    inv = root/'reports'/'ops'/'web_mobile_inventory.json'
    if not inv.exists():
        print("inventory missing:", inv); sys.exit(2)
    data = json.loads(inv.read_text('utf-8'))
    py = data.get('py',[])
    ranked = sorted(py, key=score, reverse=True)
    top = ranked[:100]
    outj = {'count': len(py), 'top': top}
    outdir = root/'reports'/'ops'
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir/'web_mobile_shortlist.json').write_text(json.dumps(outj, indent=2), encoding='utf-8')
    lines = ["# Web/Mobile Shortlist", f"- total candidates: {len(py)}", f"- top listed: {len(top)}", ""]
    lines.append("| score | frameworks | ports | routes | file |")
    lines.append("|---:|---|---|---:|---|")
    def _score(e): return score(e)
    for e in top:
        sc = _score(e)
        fr = ','.join(e.get('frameworks',[])) or '-'
        pr = ','.join(map(str,e.get('ports',[]))) or '-'
        rc = len(e.get('routes',[]))
        lines.append(f"| {sc} | {fr} | {pr} | {rc} | `{e.get('file','')}` |")
    (outdir/'web_mobile_shortlist.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print(str(outdir/'web_mobile_shortlist.md'))
if __name__=='__main__':
    main()

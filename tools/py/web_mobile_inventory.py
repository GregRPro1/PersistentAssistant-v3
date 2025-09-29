
import json, ast, re, sys
from pathlib import Path
TAG_LIBS={'flask','fastapi','starlette','aiohttp','quart','tornado','uvicorn','http.server'}
def scan_py(p):
    out={'file':str(p),'frameworks':[],'routes':[],'ports':[],'hints':[]}
    s=p.read_text('utf-8',errors='ignore')
    for lib in TAG_LIBS:
        if re.search(r'\b'+re.escape(lib)+r'\b', s): out['frameworks'].append(lib)
    for m in re.finditer(r'(?<!\w)(\d{2,5})(?!\w)', s):
        n=int(m.group(1)); 
        if 80<=n<=65535 and n not in out['ports']: out['ports'].append(n)
    try:
        t=ast.parse(s,str(p))
        for n in ast.walk(t):
            if getattr(n,'decorator_list',None):
                for d in n.decorator_list:
                    a=getattr(getattr(d,'func',None),'attr',None)
                    if a in {'get','post','put','patch','delete','route'}:
                        out['routes'].append({'fn':getattr(n,'name',''), 'method':a.upper()})
    except: pass
    if 'http.server' in out['frameworks']: out['hints'].append('stdlib-http-server')
    return out
def main(root):
    r=Path(root).resolve()
    pys=[]; assets=[]; ps1=[]
    for p in r.rglob('*'):
        if p.is_dir(): continue
        sfx=p.suffix.lower()
        if sfx=='.py':
            info=scan_py(p)
            if info['frameworks'] or info['routes'] or info['ports'] or info['hints']: pys.append(info)
        elif sfx in ('.html','.htm','.js','.json','.css'):
            if any(k in p.parts for k in ('web','docs','templates','static','public')):
                assets.append(str(p))
        elif sfx=='.ps1':
            txt=p.read_text('utf-8',errors='ignore').lower()
            if 'run_control_api.ps1' in txt or 'run_pack_fetcher.ps1' in txt:
                ps1.append(str(p))
    out={'root':str(r),'py':pys,'assets':assets,'ps1':ps1}
    d=r/'reports'/'ops'; d.mkdir(parents=True,exist_ok=True)
    (d/'web_mobile_inventory.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
    (d/'web_mobile_inventory.md').write_text('# Web/Mobile Inventory\n- py: {}\n- assets: {}\n- ps1: {}\n'.format(len(pys),len(assets),len(ps1)),encoding='utf-8')
if __name__=='__main__':
    main(sys.argv[1] if len(sys.argv)>1 else '.')

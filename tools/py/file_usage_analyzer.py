import argparse, os, ast
from pathlib import Path

def find_py_files(root: Path):
    for p in root.rglob('*.py'):
        # skip venvs and staging
        sp = str(p).lower()
        if any(s in sp for s in ['.venv','_staging','__pycache__']):
            continue
        yield p

def analyze(root: Path):
    files=list(find_py_files(root))
    imports={p: set() for p in files}
    for p in files:
        try:
            tree=ast.parse(p.read_text(encoding='utf-8', errors='ignore'))
        except Exception:
            continue
        for n in ast.walk(tree):
            if isinstance(n,(ast.Import,ast.ImportFrom)):
                mod = getattr(n,'module',None)
                names=[a.name for a in getattr(n,'names',[]) or []]
                if mod: imports[p].add(mod.split('.')[0])
                for nm in names: imports[p].add(nm.split('.')[0])
    return {'files': len(files), 'sample': sorted(str(p) for p in list(files)[:10])}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--root', required=True); ap.add_argument('--out', required=True)
    a=ap.parse_args(); root=Path(a.root)
    res=analyze(root)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    with open(a.out,'w',encoding='utf-8') as f:
        f.write(str(res))

if __name__=='__main__': main()

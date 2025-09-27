import ast, json
from pathlib import Path
def find_py_files(root: Path):
    return [p for p in root.rglob('*.py') if not any(s in p.parts for s in ['.venv','_staging','__pycache__'])]
def build_import_index(py_files):
    idx={}
    for p in py_files:
        try: tree=ast.parse(p.read_text(encoding='utf-8', errors='ignore'))
        except Exception: continue
        names=set()
        for n in ast.walk(tree):
            if isinstance(n,(ast.Import,ast.ImportFrom)):
                if isinstance(n,ast.Import):
                    for a in n.names: names.add(a.name.split('.')[0])
                else:
                    if n.module: names.add(n.module.split('.')[0])
        idx[p.as_posix()]=sorted(names)
    return idx
def main():
    import argparse, json
    ap=argparse.ArgumentParser(); ap.add_argument('--root', default='.' ); ap.add_argument('--out', default='reports/usage/unused_files.json')
    a=ap.parse_args(); root=Path(a.root)
    idx=build_import_index(find_py_files(root))
    out=Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({'import_index': idx}, indent=2), encoding='utf-8')
if __name__=='__main__': main()

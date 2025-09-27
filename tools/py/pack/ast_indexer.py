import argparse, json, ast, sys
from pathlib import Path

def read_text(p: Path) -> str:
    try: return p.read_text(encoding="utf-8", errors="ignore")
    except Exception: return ""

def annotate_parents(tree: ast.AST) -> None:
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            setattr(child, "parent", parent)

def build_index(py_files):
    idx = {}
    for f in py_files:
        src = read_text(f)
        if not src.strip(): 
            continue
        try:
            tree = ast.parse(src, filename=str(f))
            annotate_parents(tree)
        except Exception as e:
            idx[str(f)] = {"error": f"parse_failed: {type(e).__name__}: {e}"}
            continue

        imports, classes, functions = [], {}, []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports += [n.name for n in node.names]
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                imports += [f"{mod}:{n.name}" for n in node.names]
            elif isinstance(node, ast.ClassDef):
                methods = [b.name for b in node.body if isinstance(b, ast.FunctionDef)]
                classes[node.name] = sorted(methods)
            elif isinstance(node, ast.FunctionDef):
                if isinstance(getattr(node, "parent", None), ast.Module) or not hasattr(node, "parent"):
                    functions.append(node.name)
        idx[str(f)] = {
            "imports": sorted(set(imports)),
            "classes": classes,
            "functions": sorted(set(functions)),
        }
    return idx

def discover_roots(roots):
    ignored = {".git", ".venv", "venv", "tmp", "dist", "build", "__pycache__"}
    files = []
    for r in roots:
        p = Path(r)
        if p.is_file() and p.suffix.lower()==".py":
            files.append(p)
        elif p.is_dir():
            for sub in p.rglob("*.py"):
                if any(part in ignored for part in sub.parts):
                    continue
                files.append(sub)
    return files

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default="tmp/logs")
    ap.add_argument("--name", default="sb_ast_now")
    ap.add_argument("--roots", nargs="*", default=["."])
    args = ap.parse_args()

    outdir = Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)
    base = args.name
    py_files = discover_roots(args.roots)
    idx = build_index(py_files)

    jpath = outdir / f"{base}_ast_index.json"
    jpath.write_text(json.dumps(idx, indent=2), encoding="utf-8")
    try:
        import yaml
        ypath = outdir / f"{base}_ast_index.yaml"
        ypath.write_text(yaml.safe_dump(idx, sort_keys=False), encoding="utf-8")
        print(str(jpath)); print(str(ypath))
    except Exception:
        print(str(jpath))
    return 0

if __name__ == "__main__":
    sys.exit(main())

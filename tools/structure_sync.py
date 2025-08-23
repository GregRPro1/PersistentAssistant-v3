# structure_sync.py
# Persistent Assistant v3
# Created: 2025-08-18
# Author: G. Rapson
# Company: GR-Analysis
# Description:
#   Scans the project and writes a concise structural snapshot with
#   key metadata for each source/document file to YAML (and a short MD).
#   Adds function/method signatures and first docstring lines (no bodies).

from __future__ import annotations
# --- PA_ROOT_IMPORT ---
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# --- /PA_ROOT_IMPORT ---
import os
import re
import ast
import sys
import yaml
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# --- Windows stdout safety: prefer UTF-8, but don't fail if unsupported ---
import sys
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # Python 3.7+
except Exception:
    pass

# -------- config helpers --------

def resolve_project_root() -> Path:
    """
    Try to read config/project_config.yaml to get root_path, otherwise
    fall back to the parent of this script (../).
    """
    here = Path(__file__).resolve()
    repo_root_guess = here.parents[1]  # .../PersistentAssistant
    cfg = repo_root_guess / "config" / "project_config.yaml"
    if cfg.exists():
        try:
            data = yaml.safe_load(cfg.read_text(encoding="utf-8"))
            root = Path(data.get("root_path", str(repo_root_guess)))
            return root
        except Exception:
            return repo_root_guess
    return repo_root_guess

# -------- utils --------

COMMENT_RE = re.compile(r"^\s*#")

def extract_header_comment(text: str, max_lines: int = 20) -> str:
    """Extract the leading contiguous comment block (file header)."""
    lines = text.splitlines()
    header = []
    for i, line in enumerate(lines[:max_lines]):
        if i == 0 and line.strip().startswith("#!"):  # shebang, keep it
            header.append(line)
            continue
        if COMMENT_RE.match(line):
            header.append(line)
        elif line.strip() == "":
            if header:
                header.append(line)
            else:
                break
        else:
            break
    return "\n".join(header).strip()

def nonblank_sloc(text: str) -> int:
    """Count non-blank, non-comment lines."""
    n = 0
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        n += 1
    return n

def sha1_hex(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()

def safe_unparse(node: ast.AST) -> str:
    try:
        return ast.unparse(node)  # py>=3.9
    except Exception:
        return ""

def format_args(args: ast.arguments) -> str:
    parts = []

    # pos-only
    if getattr(args, "posonlyargs", []):
        for a in args.posonlyargs:
            ann = f": {safe_unparse(a.annotation)}" if a.annotation else ""
            parts.append(f"{a.arg}{ann}")
        parts.append("/")

    # normal args
    for a in args.args:
        ann = f": {safe_unparse(a.annotation)}" if a.annotation else ""
        parts.append(f"{a.arg}{ann}")

    # vararg *args
    if args.vararg:
        ann = f": {safe_unparse(args.vararg.annotation)}" if args.vararg.annotation else ""
        parts.append(f"*{args.vararg.arg}{ann}")

    # kw-only separator if needed
    if args.kwonlyargs and not args.vararg:
        parts.append("*")

    # kw-only args
    for a in args.kwonlyargs:
        ann = f": {safe_unparse(a.annotation)}" if a.annotation else ""
        parts.append(f"{a.arg}{ann}")

    # **kwargs
    if args.kwarg:
        ann = f": {safe_unparse(args.kwarg.annotation)}" if args.kwarg.annotation else ""
        parts.append(f"**{args.kwarg.arg}{ann}")

    return ", ".join(parts)

def doc_first_line(doc: str | None) -> str | None:
    if not doc:
        return None
    return doc.strip().splitlines()[0].strip() or None

# -------- Python AST extraction --------

def parse_python_ast(text: str) -> Dict[str, Any]:
    """
    Parse Python for module docstring, imports, classes (with method signatures),
    and top-level functions (with signatures).
    """
    out: Dict[str, Any] = {
        "docstring": None,
        "imports": [],
        "functions": [],  # list of {name, signature, doc1line}
        "classes": [],    # list of {name, methods: [{name, signature, doc1line}]}
        "contains_main": False,
    }
    try:
        tree = ast.parse(text)
    except Exception as e:
        out["error"] = f"AST parse error: {e}"
        return out

    out["docstring"] = ast.get_docstring(tree)

    imports = set()
    contains_main = False
    functions = []
    classes = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module.split(".")[0])
        elif isinstance(node, ast.If):
            try:
                test_src = ast.get_source_segment(text, node.test) or ""
                if "__name__" in test_src and "__main__" in test_src:
                    contains_main = True
            except Exception:
                pass

    # top-level functions only
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            sig = f"({format_args(node.args)})"
            ret = f" -> {safe_unparse(node.returns)}" if node.returns else ""
            functions.append({
                "name": node.name,
                "signature": f"{node.name}{sig}{ret}",
                "doc1line": doc_first_line(ast.get_docstring(node)),
            })
        elif isinstance(node, ast.ClassDef):
            methods = []
            for sub in node.body:
                if isinstance(sub, ast.FunctionDef):
                    sig = f"({format_args(sub.args)})"
                    ret = f" -> {safe_unparse(sub.returns)}" if sub.returns else ""
                    methods.append({
                        "name": sub.name,
                        "signature": f"{sub.name}{sig}{ret}",
                        "doc1line": doc_first_line(ast.get_docstring(sub)),
                    })
            classes.append({
                "name": node.name,
                "methods": methods,
                "doc1line": doc_first_line(ast.get_docstring(node)),
            })

    out["imports"] = sorted(list(imports))
    out["functions"] = functions
    out["classes"] = classes
    out["contains_main"] = contains_main
    return out

# -------- YAML/MD snapshot --------

INCLUDE_EXT = {".py", ".yaml", ".yml", ".md"}

def snapshot_file(root: Path, p: Path, preview_lines: int = 10) -> Dict[str, Any]:
    rel = p.relative_to(root).as_posix()
    try:
        text = p.read_text(encoding="utf-8")
    except Exception as e:
        return {
            "file": p.name,
            "path": rel,
            "error": f"read error: {e}",
            "last_modified": datetime.fromtimestamp(p.stat().st_mtime).isoformat(),
        }

    info: Dict[str, Any] = {
        "file": p.name,
        "path": rel,
        "last_modified": datetime.fromtimestamp(p.stat().st_mtime).isoformat(),
        "lines_of_code": nonblank_sloc(text),
        "header_comment": extract_header_comment(text),
        "sha1": sha1_hex(text),
        "preview": "\n".join(text.splitlines()[:preview_lines]).strip(),
    }

    ext = p.suffix.lower()
    if ext == ".py":
        info.update(parse_python_ast(text))
    elif ext in (".yaml", ".yml"):
        # only top-level keys (short)
        try:
            y = yaml.safe_load(text)
            info["yaml_top_keys"] = list(y.keys()) if isinstance(y, dict) else []
        except Exception as e:
            info["yaml_error"] = str(e)
    elif ext == ".md":
        # first few headings
        heads = []
        for line in text.splitlines():
            s = line.lstrip()
            if s.startswith("# "):
                heads.append(s[2:].strip())
            elif s.startswith("## "):
                heads.append(s[3:].strip())
            if len(heads) >= 3:
                break
        info["headings"] = heads

    return info

def run_snapshot(root: Path, out_yaml: Path, out_md: Path, preview_lines: int = 10) -> Dict[str, Any]:
    items: List[Dict[str, Any]] = []
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in INCLUDE_EXT:
            if any(x in p.parts for x in (".venv", "venv", "__pycache__", ".git")):
                continue
            items.append(snapshot_file(root, p, preview_lines))

    items.sort(key=lambda d: d.get("path", ""))
    out_yaml.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)

    with out_yaml.open("w", encoding="utf-8") as f:
        yaml.dump(items, f, allow_unicode=True, sort_keys=False)

    # short human index
    lines = ["# Project Structure Snapshot (index)\n"]
    for it in items:
        cls_n = len(it.get("classes", [])) if "classes" in it else 0
        fn_n = len(it.get("functions", [])) if "functions" in it else 0
        loc = it.get("lines_of_code", 0)
        lines.append(f"- `{it.get('path')}` — classes:{cls_n} funcs:{fn_n} loc:{loc}")
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {"count": len(items), "yaml": str(out_yaml), "md": str(out_md)}

def main(argv: List[str]) -> int:
    root = resolve_project_root()
    out_yaml = root / "project" / "structure" / "project_structure_snapshot_full.yaml"
    out_md = root / "project" / "structure" / "project_structure_snapshot_index.md"

    res = run_snapshot(root, out_yaml, out_md, preview_lines=10)
    print(f"Snapshot complete: {res['count']} files")
    print(f"YAML: {res['yaml']}")
    print(f"MD  : {res['md']}")
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))

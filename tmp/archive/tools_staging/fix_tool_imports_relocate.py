from __future__ import annotations
import re, sys, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"

BEGIN = "# --- PA_ROOT_IMPORT ---"
END   = "# --- /PA_ROOT_IMPORT ---"
BLOCK = (
    BEGIN + "\n"
    "import sys, pathlib\n"
    "ROOT = pathlib.Path(__file__).resolve().parents[1]\n"
    "if str(ROOT) not in sys.path:\n"
    "    sys.path.insert(0, str(ROOT))\n"
    + END + "\n"
)

def split_docstring_header(lines: list[str]) -> int:
    if not lines: return 0
    i = 0
    if lines[0].startswith("#!") or "coding" in lines[0]:
        i += 1
    while i < len(lines) and (not lines[i].strip() or lines[i].lstrip().startswith("#")):
        i += 1
    if i < len(lines) and lines[i].lstrip().startswith(('"""',"'''")):
        q = lines[i].lstrip()[:3]
        j = i+1
        while j < len(lines):
            if q in lines[j]:
                return j+1
            j += 1
        return i+1
    return i

def find_future_tail(lines: list[str], start: int) -> int:
    i = start
    while i < len(lines) and lines[i].lstrip().startswith("from __future__ import"):
        i += 1
    return i

def remove_block(txt: str) -> tuple[str,bool]:
    if BEGIN not in txt: return txt, False
    out=[]; skip=False; removed=False
    for line in txt.splitlines(keepends=True):
        if not skip and line.strip().startswith(BEGIN):
            skip=True; removed=True; continue
        if skip and line.strip().startswith(END):
            skip=False; continue
        if not skip: out.append(line)
    return "".join(out), removed

def insert_block_at(txt: str, idx: int) -> str:
    lines = txt.splitlines(keepends=True)
    lines[idx:idx] = [BLOCK]
    return "".join(lines)

def relocate(path: Path) -> bool:
    txt = path.read_text(encoding="utf-8")
    txt2, _ = remove_block(txt)
    lines = txt2.splitlines(keepends=True)
    ins = split_docstring_header(lines)
    ins = find_future_tail(lines, ins)
    out = insert_block_at(txt2, ins)
    if out == txt: return False
    bak = path.with_suffix(path.suffix + ".bak.headerfix")
    shutil.copy2(str(path), str(bak))
    path.write_text(out, encoding="utf-8")
    return True

def main():
    edited=0; skipped=0
    for p in TOOLS.glob("*.py"):
        if p.name in ("__init__.py","fix_tool_imports.py","fix_tool_imports_relocate.py"):
            continue
        try:
            if relocate(p):
                print(f"[IMPORT RELOC] {p}")
                edited+=1
            else:
                skipped+=1
        except Exception as e:
            print(f"[IMPORT RELOC ERR] {p}: {e}")
    print(f"[IMPORT RELOC SUMMARY] edited={edited} skipped={skipped}")
    return 0

if __name__=="__main__":
    raise SystemExit(main())

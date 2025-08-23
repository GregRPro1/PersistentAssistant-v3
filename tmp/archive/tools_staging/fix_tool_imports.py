from __future__ import annotations
import re, sys, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
HEADER_BEGIN = "# --- PA_ROOT_IMPORT ---"
HEADER_SNIPPET = (
    HEADER_BEGIN + "\n"
    "import sys, pathlib\n"
    "ROOT = pathlib.Path(__file__).resolve().parents[1]\n"
    "if str(ROOT) not in sys.path:\n"
    "    sys.path.insert(0, str(ROOT))\n"
    "# --- /PA_ROOT_IMPORT ---\n"
)

def needs_header(txt: str) -> bool:
    return HEADER_BEGIN not in txt

def insert_header(txt: str) -> str:
    # If there's a shebang or encoding line, insert after it; else at top.
    lines = txt.splitlines(keepends=True)
    idx = 0
    if lines and (lines[0].startswith("#!") or "coding" in lines[0]):
        idx = 1
    return "".join(lines[:idx] + [HEADER_SNIPPET] + lines[idx:])

def main():
    if not TOOLS.exists():
        print(f"[IMPORT FIX] tools/ not found: {TOOLS}")
        return 2
    edited = 0
    skipped = 0
    backed  = 0
    for p in TOOLS.glob("*.py"):
        if p.name in ("__init__.py", "fix_tool_imports.py"):
            continue
        try:
            txt = p.read_text(encoding="utf-8")
        except Exception:
            skipped += 1
            continue
        if needs_header(txt):
            bak = p.with_suffix(p.suffix + ".bak.rootimport")
            shutil.copy2(str(p), str(bak))
            p.write_text(insert_header(txt), encoding="utf-8")
            backed += 1
            edited += 1
            print(f"[IMPORT FIX] injected root header -> {p}")
        else:
            skipped += 1
    print(f"[IMPORT FIX SUMMARY] edited={edited} backed_up={backed} skipped={skipped}")
    return 0

if __name__=="__main__":
    raise SystemExit(main())

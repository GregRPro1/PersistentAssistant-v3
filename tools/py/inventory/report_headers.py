# tools/py/inventory/report_headers.py
# Extract header comments and top MD headings; write insights YAMLs.
from __future__ import annotations
import sys, json, yaml, pathlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]  # repo root
OUT_DIR = ROOT / "data" / "insights"
OUT_HEADERS = OUT_DIR / "file_headers.yaml"
OUT_MDHEADS = OUT_DIR / "md_headings.yaml"
MANIFEST_CANDIDATES = [
    ROOT / "project" / "structure" / "file_manifest.yaml",
    ROOT / "project" / "structure" / "file_manifest.yml",
]

def load_manifest() -> list[dict]:
    for p in MANIFEST_CANDIDATES:
        if p.exists():
            try:
                data = yaml.safe_load(p.read_text(encoding="utf-8"))
            except Exception as e:
                print(f"Manifest read error: {p} -> {e}", file=sys.stderr)
                sys.exit(1)
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                for k in ("files", "items", "entries", "list", "data"):
                    v = data.get(k)
                    if isinstance(v, list):
                        return v
            print("Manifest is not a list (no files/items/entries/list/data key).", file=sys.stderr)
            sys.exit(1)
    print("Manifest not found.", file=sys.stderr)
    sys.exit(1)

def extract_header_comment(text: str, max_lines: int = 20) -> str:
    lines = text.splitlines()
    block = []
    for i, line in enumerate(lines[:max_lines]):
        s = line.rstrip("\n")
        if i == 0 and s.strip().startswith("#!"):
            block.append(s); continue
        if s.strip().startswith("#"):
            block.append(s); continue
        if s.strip() == "":
            if block: block.append(s); continue
            else: break
        break
    return "\n".join(block).strip()

def md_top_headings(text: str, max_n: int = 8) -> list[str]:
    out = []
    for s in text.splitlines():
        t = s.lstrip()
        if t.startswith("# "):   out.append(t[2:].strip())
        elif t.startswith("## "): out.append(t[3:].strip())
        if len(out) >= max_n: break
    return out

def read_text(path: Path) -> str|None:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None

def main() -> int:
    items = load_manifest()
    headers = []
    mdheads = []
    for it in items:
        rel = it.get("path") or it.get("rel") or it.get("file")
        if not rel: continue
        p = (ROOT / rel).resolve()
        if not p.exists(): continue
        if p.suffix.lower() in (".py", ".yaml", ".yml", ".md"):
            txt = read_text(p)
            if txt is None: continue
            if p.suffix.lower() == ".md":
                heads = md_top_headings(txt)
                if heads:
                    mdheads.append({"path": rel, "headings": heads})
            else:
                hdr = extract_header_comment(txt)
                if hdr:
                    headers.append({"path": rel, "header": hdr})
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_HEADERS.write_text(yaml.safe_dump(headers, sort_keys=False, allow_unicode=True), encoding="utf-8")
    OUT_MDHEADS.write_text(yaml.safe_dump(mdheads, sort_keys=False, allow_unicode=True), encoding="utf-8")
    print(json.dumps({"ok": True, "wrote": [str(OUT_HEADERS), str(OUT_MDHEADS)]}, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())


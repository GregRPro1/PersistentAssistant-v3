from __future__ import annotations
import os, re, sys, json, hashlib, time, pathlib, argparse, urllib.request, urllib.error
from typing import Any, Dict, List, Optional

try:
    import yaml
except Exception:
    yaml = None  # YAML optional (we still produce JSON/MD)

ROOT = pathlib.Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
OVERLAY = TOOLS / "tool_catalog.overlay.yaml"
OUT_YAML = TOOLS / "tool_catalog.yaml"
OUT_JSON = TOOLS / "tool_catalog.json"
OUT_MD   = TOOLS / "tool_catalog.md"

SKIP_PARTS = {".git","__pycache__","venv",".venv","tmp","node_modules"}
PS1_PARAM_RE = re.compile(r"^\s*param\s*\((.*?)\)", re.IGNORECASE | re.DOTALL)
PS1_PARAM_ITEM_RE = re.compile(r"\[(?P<type>[^\]]+)\]\$(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*(?:=\s*(?P<default>[^,\)]+))?")

def sha1_text(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8", "replace")).hexdigest()

def read_text(p: pathlib.Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except Exception:
        try:
            return p.read_text(encoding="latin-1")
        except Exception as e:
            return f""  # unreadable; handled later

def header_comment_ps(text: str, max_lines: int = 24) -> str:
    lines = text.splitlines()
    out = []
    for i, ln in enumerate(lines[:max_lines]):
        s = ln.strip()
        if s.startswith("#") or (i == 0 and s.startswith("##")):
            out.append(ln)
        elif s == "" and out:
            out.append(ln)
        else:
            if not out and s.lower().startswith("[cmdletbinding()]"):
                out.append(ln)
                continue
            break
    return "\n".join(out).strip()

def module_docstring_py(text: str, max_len: int = 800) -> str:
    # quick/robust: """...""" or '''...''' at top
    m = re.match(r'^\s*(?P<q>["\']{3})(?P<doc>.*?)(?P=q)', text, re.DOTALL)
    if m:
        return (m.group("doc") or "").strip()[:max_len]
    return ""

def parse_ps_params(text: str) -> List[Dict[str, Any]]:
    m = PS1_PARAM_RE.search(text)
    if not m:
        return []
    body = m.group(1)
    out: List[Dict[str, Any]] = []
    for pm in PS1_PARAM_ITEM_RE.finditer(body):
        out.append({
            "name": pm.group("name"),
            "type": (pm.group("type") or "").strip(),
            "default": (pm.group("default") or "").strip()
        })
    return out

def find_scripts() -> List[pathlib.Path]:
    paths: List[pathlib.Path] = []
    if TOOLS.exists():
        for p in TOOLS.rglob("*"):
            if not p.is_file(): continue
            if any(part in SKIP_PARTS for part in p.parts): continue
            if p.suffix.lower() in (".ps1",".py"):
                paths.append(p)
    return paths

def is_ps1(p: pathlib.Path) -> bool: return p.suffix.lower() == ".ps1"
def is_py (p: pathlib.Path) -> bool: return p.suffix.lower() == ".py"

def auto_usage(p: pathlib.Path) -> str:
    rel = p.relative_to(ROOT).as_posix()
    if is_ps1(p):
        return f"powershell -NoProfile -ExecutionPolicy Bypass -File {rel}"
    return f"python {rel}"

def tool_id_for(p: pathlib.Path) -> str:
    rel = p.relative_to(ROOT).as_posix()
    kind = "ps" if is_ps1(p) else "py"
    return f"{kind}:{rel}"

def scrape_file(p: pathlib.Path) -> Dict[str, Any]:
    s = read_text(p)
    stat = p.stat()
    desc = ""
    params: List[Dict[str,Any]] = []
    if is_ps1(p):
        desc = header_comment_ps(s)
        params = parse_ps_params(s)
    elif is_py(p):
        desc = module_docstring_py(s)
    return {
        "id": tool_id_for(p),
        "name": p.stem,
        "kind": "ps" if is_ps1(p) else "py",
        "path": p.relative_to(ROOT).as_posix(),
        "usage": auto_usage(p),
        "description": desc,
        "params": params,
        "last_modified": int(stat.st_mtime),
        "bytes": int(stat.st_size),
        "sha1": sha1_text(s),
        "source": "auto"
    }

def fetch_routes(host: str, port: int) -> List[Dict[str, Any]]:
    url = f"http://{host}:{port}/__routes__"
    try:
        with urllib.request.urlopen(url, timeout=2.5) as r:
            body = r.read().decode("utf-8","replace")
            obj = json.loads(body)
            routes = obj.get("routes") or []
            out = []
            for r in routes:
                rule = str(r.get("rule",""))
                if "/agent" in rule or "/phone" in rule or "/health" in rule:
                    out.append({
                        "id": f"endpoint:{rule}",
                        "name": rule,
                        "kind": "endpoint",
                        "path": rule,
                        "usage": f"GET {rule}",
                        "description": f"Flask route ({','.join(r.get('methods') or [])})",
                        "params": [],
                        "last_modified": None,
                        "bytes": None,
                        "sha1": None,
                        "source": "live"
                    })
            return out
    except Exception:
        return []

def load_overlay() -> Dict[str, Any]:
    if not OVERLAY.exists() or not yaml:
        return {}
    try:
        data = yaml.safe_load(OVERLAY.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}

def apply_overlay(tools: List[Dict[str, Any]], overlay: Dict[str, Any]) -> None:
    # overlay schema: { overrides: { <id>: {title, description, usage, tags, contact, ...} } }
    ov = overlay.get("overrides") if isinstance(overlay, dict) else None
    if not isinstance(ov, dict): return
    by_id = {t["id"]: t for t in tools}
    for oid, meta in ov.items():
        if not isinstance(meta, dict): continue
        if oid in by_id:
            by_id[oid].update(meta)
            by_id[oid]["source"] = f"{by_id[oid].get('source','auto')}+overlay"
        else:
            # allow overlay-only entries
            x = dict(meta)
            x["id"] = oid
            x.setdefault("source","overlay")
            tools.append(x)

def write_outputs(tools: List[Dict[str, Any]]) -> None:
    # sort by kind then name
    tools.sort(key=lambda t: (t.get("kind",""), t.get("name",""), t.get("path","")))
    # JSON
    OUT_JSON.write_text(json.dumps({"version":1,"generated_at":int(time.time()),"tools":tools}, indent=2), encoding="utf-8")
    # YAML
    if yaml:
        OUT_YAML.write_text(yaml.safe_dump({"version":1,"generated_at":int(time.time()),"tools":tools}, sort_keys=False, allow_unicode=True), encoding="utf-8")
    # MD
    lines = ["# Tool Catalog\n"]
    for t in tools:
        nm = t.get("name","")
        k  = t.get("kind","")
        p  = t.get("path","")
        u  = t.get("usage","")
        d  = (t.get("description") or "").splitlines()[0] if t.get("description") else ""
        lines.append(f"- **{nm}** ({k}) — `{p}`  \n  usage: `{u}`  \n  {d}")
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8782)
    args = ap.parse_args()

    tools: List[Dict[str, Any]] = []
    for p in find_scripts():
        tools.append(scrape_file(p))
    # live endpoints (best-effort)
    tools.extend(fetch_routes(args.host, args.port))
    # overlay merge
    apply_overlay(tools, load_overlay())
    # emit
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    write_outputs(tools)
    print(f"Wrote: {OUT_JSON}")
    if yaml: print(f"Wrote: {OUT_YAML}")
    print(f"Wrote: {OUT_MD}")
    return 0

if __name__ == "__main__":
    sys.exit(main())

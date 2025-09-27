from __future__ import annotations
import argparse, json, pathlib

def _read(p: pathlib.Path) -> str:
    return p.read_text(encoding='utf-8') if p.exists() else ''

def _write(p: pathlib.Path, s: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s, encoding='utf-8')

def ensure_allow(path: pathlib.Path, globs: list[str]) -> dict:
    raw = _read(path)
    if "allow_globs:" not in raw:
        raw += "\nallow_globs:\n"
    lines = raw.splitlines()
    out = []
    in_allow = False
    existing = set()
    for ln in lines:
        if ln.strip().startswith("allow_globs:"):
            in_allow = True
            out.append(ln)
            continue
        if in_allow:
            if ln.strip().startswith("- "):
                out.append(ln)
                existing.add(ln.strip()[2:].strip().strip('"'))
                continue
            else:
                # leaving block
                for g in globs:
                    if g not in existing:
                        out.append(f'  - "{g}"')
                in_allow = False
                out.append(ln)
        else:
            out.append(ln)
    if in_allow:
        for g in globs:
            if g not in existing:
                out.append(f'  - "{g}"')
    new = "\n".join(out) + "\n"
    _write(path, new)
    return {"ok": True, "path": str(path), "added": [g for g in globs if g not in existing]}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default="config/runner_policy.yaml")
    ap.add_argument("--add-allow", nargs="+", default=[])
    args = ap.parse_args()
    res = ensure_allow(pathlib.Path(args.file), args.add_allow)
    print(json.dumps(res))
if __name__ == "__main__":
    main()

from __future__ import annotations
import argparse, json, hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

def sha256_hex(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def add_file(files: list[dict], rel: str) -> None:
    p = (ROOT / rel).resolve()
    if p.exists() and p.is_file():
        files.append({
            "rel": rel.replace("\\\\","/"),
            "bytes": p.stat().st_size,
            "sha256": sha256_hex(p),
        })

def build_pack(plan_path: Path) -> dict:
    files: list[dict] = []
    # always include plan + policy
    add_file(files, "project/plans/project_plan_v3.yaml")
    add_file(files, "config/runner_policy.yaml")
    # helpful docs
    for rel in ["docs/USER_GUIDE.md", "docs/GLOSSARY.md"]:
        add_file(files, rel)
    # agentic code
    agdir = ROOT / "tools/py/agentic"
    if agdir.exists():
        for p in sorted(agdir.glob("*.py")):
            try:
                rel = p.relative_to(ROOT).as_posix()
                add_file(files, rel)
            except Exception:
                pass
    return {
        "root": str(ROOT),
        "plan": str(plan_path),
        "files": files,
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", default=str(ROOT / "project/plans/project_plan_v3.yaml"))
    ap.add_argument("--out",  default=str(ROOT / "tmp/context/context_pack.json"))
    args = ap.parse_args()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    pack = build_pack(Path(args.plan))
    out.write_text(json.dumps(pack, indent=2), encoding="utf-8")
    print(str(out))

if __name__ == "__main__":
    main()

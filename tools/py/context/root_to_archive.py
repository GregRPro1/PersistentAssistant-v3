#!/usr/bin/env python3
from pathlib import Path

KEEP = {
    "README.md","LICENSE",".gitignore",".gitattributes",".editorconfig",
    "pyproject.toml","requirements.txt","requirements-dev.txt",
    "Dockerfile","docker-compose.yml","compose.yml","compose.yaml",
    "Makefile","setup.cfg","main.py","moves_map.yml",
}

def main():
    repo = Path(".").resolve()
    ctx  = Path("_context/PAL20251020B")
    ctx.mkdir(parents=True, exist_ok=True)
    arch = ctx / "archive_candidates.txt"
    existing = set()
    if arch.exists():
        existing = {l.strip().replace("\\","/") for l in arch.read_text(encoding="utf-8").splitlines() if l.strip()}

    added = 0
    lines = []
    for p in sorted(repo.glob("*")):
        if not p.is_file(): continue
        if p.name in KEEP: continue
        rel = p.relative_to(repo).as_posix()
        if rel not in existing:
            lines.append(rel); added += 1

    if lines:
        with arch.open("a", encoding="utf-8") as f:
            for rel in lines: f.write(rel + "\n")
    print(f"[OK] root files added to archive list: {added}")

if __name__ == "__main__":
    main()

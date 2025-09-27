# server/micro_projects.py
from __future__ import annotations
from flask import Blueprint, request, jsonify
from pathlib import Path
from datetime import datetime, UTC
import re, json, os, threading

try:
    import yaml  # PyYAML
except Exception:
    yaml = None  # we'll still create files even if registry can’t be YAML-serialized

ROOT = Path(__file__).resolve().parents[2]   # …/server -> repo root
WORKSPACES = ROOT / "workspaces"
REGISTRY = ROOT / "project" / "projects.yaml"
_LOCK = threading.Lock()

ID_RE = re.compile(r"^[a-z0-9][a-z0-9_\-]{1,38}[a-z0-9]$")  # 3..40 chars, safe

bp = Blueprint("micro_projects", __name__, url_prefix="/agent")

def _load_registry() -> list[dict]:
    if not REGISTRY.exists():
        return []
    try:
        if yaml:
            data = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        # fallback JSON (if someone converted it)
        return json.loads(REGISTRY.read_text(encoding="utf-8"))
    except Exception:
        return []

def _save_registry(items: list[dict]) -> None:
    REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    if yaml:
        REGISTRY.write_text(yaml.safe_dump(items, sort_keys=False, allow_unicode=True), encoding="utf-8")
    else:
        REGISTRY.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")

def _safe_write(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")

def _scaffold_basic(root: Path, meta: dict) -> list[str]:
    created: list[str] = []
    dirs = [
        "config", "data", "data/raw", "data/processed",
        "docs", "notebooks", "results", "scripts", "src", "tests"
    ]
    for d in dirs:
        (root / d).mkdir(parents=True, exist_ok=True)
        created.append(str((root / d).as_posix()))
        # keep empty dirs in git if needed
        (root / d / ".gitkeep").write_text("", encoding="utf-8")

    _safe_write(root / "README.md",
f"""# {meta['title']}

Project ID: `{meta['id']}`  
Created: {meta['created_at']}

## Notes
- Start coding in `src/`
- Put raw data in `data/raw/` (ignored from git if you wish)
- Keep results in `results/`
""")
    created.append(str((root / "README.md").as_posix()))

    _safe_write(root / "config" / "project.yaml",
f"""id: {meta['id']}
title: {meta['title']}
template: {meta['template']}
created_at: {meta['created_at']}
description: {meta.get('description', '')}
status: new
""")
    created.append(str((root / "config" / "project.yaml").as_posix()))

    _safe_write(root / "src" / "main.py",
f"""# Entry for {meta['id']}
def main():
    print("Hello from {meta['id']}")

if __name__ == "__main__":
    main()
""")
    created.append(str((root / "src" / "main.py").as_posix()))
    return created

@bp.post("/project/new")
def create_project():
    payload = request.get_json(silent=True) or {}
    pid = str(payload.get("id", "")).strip().lower()
    title = str(payload.get("title", "")).strip()
    desc = str(payload.get("description", "")).strip()
    template = str(payload.get("template", "basic")).strip().lower() or "basic"

    if not pid or not ID_RE.match(pid):
        return jsonify({"ok": False, "error": "bad_id",
                        "hint": "Use 3-40 chars: lowercase letters, digits, -, _"}), 400
    if not title:
        return jsonify({"ok": False, "error": "missing_title"}), 400

    with _LOCK:
        reg = _load_registry()
        if any(it.get("id") == pid for it in reg):
            return jsonify({"ok": False, "error": "exists_in_registry"}), 409

        root = WORKSPACES / pid
        if root.exists():
            return jsonify({"ok": False, "error": "exists_on_disk"}), 409

        created_at = datetime.now(UTC).isoformat()
        meta = {"id": pid, "title": title, "template": template,
                "created_at": created_at, "description": desc}

        root.mkdir(parents=True, exist_ok=False)
        created = []
        if template == "basic":
            created = _scaffold_basic(root, meta)
        else:
            # future templates hook
            created = _scaffold_basic(root, meta)

        # update registry
        reg.append({
            "id": pid,
            "title": title,
            "template": template,
            "root": str(root.as_posix()),
            "created_at": created_at,
            "status": "new"
        })
        _save_registry(reg)

    return jsonify({
        "ok": True,
        "project": {
            "id": pid, "title": title, "template": template,
            "root": str(root.as_posix())
        },
        "created": created,
        "registry": str(REGISTRY.as_posix())
    })

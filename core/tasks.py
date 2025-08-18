# tasks.py
# Persistent Assistant v3
# Created: 2025-08-18
# Author: G. Rapson
# Company: GR-Analysis
# Description:
#   Generates improvement task YAML files from the introspection report.
#   Writes individual task files and an aggregated index.

from __future__ import annotations
import os
import yaml
import datetime
import re
from typing import Dict, Any, List

REPORT_PATH = os.path.join("data", "insights", "introspection_report.yaml")
TICKETS_DIR = os.path.join("data", "tickets")
INDEX_PATH  = os.path.join(TICKETS_DIR, "index.yaml")

SAFE_RE = re.compile(r"[^a-zA-Z0-9._-]+")

ISSUE_TITLES = {
    "missing_standard_header": "Add standard file header",
    "missing_module_docstring": "Add module docstring",
    "function_missing_doc": "Add function docstrings",
    "class_missing_doc": "Add class docstrings",
    "method_missing_doc": "Add method docstrings",
    "module_too_small": "Review tiny module (validate or merge)",
    "module_too_large": "Refactor large module",
}

def _safe_stem(path: str) -> str:
    stem = path.replace("\\", "/").rsplit("/", 1)[-1]
    stem = stem.rsplit(".", 1)[0]
    stem = SAFE_RE.sub("-", stem).strip("-")
    return stem or "file"

def _load_report(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Introspection report not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict) or "findings" not in data:
        raise ValueError("Invalid report format: missing 'findings'")
    return data

def _load_index(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {"tasks": []}
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if "tasks" not in data or not isinstance(data["tasks"], list):
        data["tasks"] = []
    return data

def _save_index(path: str, index: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(index, f, allow_unicode=True, sort_keys=False)

def _write_task_file(directory: str, payload: Dict[str, Any]) -> str:
    os.makedirs(directory, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    stem = f"{_safe_stem(payload.get('file_path','file'))}_{payload.get('issue','issue')}"
    filename = f"task_{ts}_{stem}.yaml"
    full = os.path.join(directory, filename)
    with open(full, "w", encoding="utf-8") as f:
        yaml.dump(payload, f, allow_unicode=True, sort_keys=False)
    return full

def _default_title(issue: str, file_path: str) -> str:
    base = ISSUE_TITLES.get(issue, f"Resolve issue '{issue}'")
    return f"{base}: {file_path}"

def create_tasks_from_introspection(report_path: str = REPORT_PATH) -> Dict[str, Any]:
    """
    Reads the introspection report and creates task YAML files per finding.
    Returns a summary dict with counts.
    """
    report = _load_report(report_path)
    findings: List[Dict[str, Any]] = report.get("findings", [])
    if not findings:
        return {"created": 0, "files_affected": 0, "index_path": INDEX_PATH, "tickets_dir": TICKETS_DIR}

    index = _load_index(INDEX_PATH)
    created_paths: List[str] = []
    seen_keys = set()  # de-duplicate tasks per (file, issue, name) where relevant

    for f in findings:
        file_path = f.get("path", "")
        issue     = f.get("issue", "unknown_issue")
        detail    = f.get("detail", "")

        # optional: include function/class names in task title if available
        # We try to parse from detail when it's "Function 'name'.../Class 'X'.../Method 'X.y'..."
        m = re.search(r"(Function|Class|Method) '([^']+)'", detail)
        symbol = m.group(2) if m else None

        dedupe_key = (file_path, issue, symbol)
        if dedupe_key in seen_keys:
            continue
        seen_keys.add(dedupe_key)

        payload = {
            "title": _default_title(issue, file_path),
            "status": "open",
            "issue": issue,
            "file_path": file_path,
            "symbol": symbol,
            "detail": detail,
            "source": "introspection_v1",
            "created": datetime.datetime.now().isoformat(),
            "priority": "normal",
            "labels": ["auto", "introspection", issue],
            "acceptance_criteria": [
                "Code compiles & existing functionality preserved",
                "Add/Update docstrings/headers where applicable",
                "Ensure tests/lints (if any) pass",
            ],
        }

        task_file = _write_task_file(TICKETS_DIR, payload)
        created_paths.append(task_file)

        # update index
        index["tasks"].append({
            "file": os.path.basename(task_file),
            "path": task_file.replace("\\", "/"),
            "title": payload["title"],
            "issue": issue,
            "file_path": file_path,
            "status": "open",
            "created": payload["created"],
            "labels": payload["labels"],
        })

    _save_index(INDEX_PATH, index)

    # summary
    files_affected = len({t["file_path"] for t in findings if "file_path" in t})
    return {
        "created": len(created_paths),
        "files_affected": files_affected,
        "index_path": INDEX_PATH,
        "tickets_dir": TICKETS_DIR,
    }

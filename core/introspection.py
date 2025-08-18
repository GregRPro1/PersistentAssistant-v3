# core/introspection.py
# Persistent Assistant v3
# Created: 2025-08-18
# Author: G. Rapson
# Company: GR-Analysis
# Description:
#   Reads the structure snapshot and writes a YAML introspection report with
#   actionable findings: missing headers, missing docstrings, empty/large modules, etc.

from __future__ import annotations
import os
import yaml
from typing import Dict, Any, List

SNAPSHOT_PATH = os.path.join("project", "structure", "project_structure_snapshot_full.yaml")
REPORT_PATH   = os.path.join("data", "insights", "introspection_report.yaml")

# Thresholds (tune later)
LOC_EMPTY_MAX = 5          # <= 5 LOC considered (near-)empty
LOC_LARGE_MIN = 300        # >= 300 LOC considered large

REQUIRED_HEADER_KEYS = [
    "#",                     # Any comment header at all
    "Persistent Assistant v",# Project marker in header comment
    "Author:",               # Author line
    "Company:",              # Company line
    "Description:",          # Description line
]

def _has_required_header(header_comment: str | None) -> bool:
    if not header_comment:
        return False
    text = header_comment
    for needle in REQUIRED_HEADER_KEYS:
        if needle not in text:
            return False
    return True

def _first_line(s: str | None) -> str:
    if not s:
        return ""
    return s.strip().splitlines()[0].strip()

def generate_introspection_report(snapshot_path: str = SNAPSHOT_PATH,
                                  report_path: str = REPORT_PATH) -> Dict[str, Any]:
    """
    Reads the project_structure_snapshot_full.yaml and writes a findings report.
    Returns the in-memory report dict for UI display/logging.

    Raises:
        FileNotFoundError: if the snapshot file is missing.
        Exception: for YAML parse or unexpected errors.
    """
    if not os.path.exists(snapshot_path):
        raise FileNotFoundError(f"Snapshot not found: {snapshot_path}")

    with open(snapshot_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, list):
        raise ValueError("Snapshot content invalid: expected list of file entries.")

    total_files = len(data)
    py_files    = [d for d in data if d.get("path", "").endswith(".py")]
    yaml_files  = [d for d in data if d.get("path", "").endswith((".yaml", ".yml"))]
    md_files    = [d for d in data if d.get("path", "").endswith(".md")]

    findings: List[Dict[str, Any]] = []

    for entry in py_files:
        path = entry.get("path", "")
        loc  = int(entry.get("lines_of_code", 0))
        header_comment = entry.get("header_comment")
        mod_doc = entry.get("docstring")  # module docstring (from AST parse)

        # Missing standard header
        if not _has_required_header(header_comment):
            findings.append({
                "path": path,
                "issue": "missing_standard_header",
                "detail": "Header comment missing or incomplete (required keys not found).",
            })

        # Module docstring missing
        if not mod_doc:
            findings.append({
                "path": path,
                "issue": "missing_module_docstring",
                "detail": "Top-level module docstring is missing.",
            })

        # Empty / near-empty module
        if loc <= LOC_EMPTY_MAX:
            findings.append({
                "path": path,
                "issue": "module_too_small",
                "detail": f"Module has very few nonblank LOC ({loc} <= {LOC_EMPTY_MAX}).",
            })

        # Oversized module
        if loc >= LOC_LARGE_MIN:
            findings.append({
                "path": path,
                "issue": "module_too_large",
                "detail": f"Module is large ({loc} >= {LOC_LARGE_MIN} LOC). Consider refactor.",
            })

        # Functions & classes docstrings
        for fn in entry.get("functions", []):
            # entry['functions'] is list of dicts when using upgraded structure_sync
            name = fn.get("name") if isinstance(fn, dict) else str(fn)
            doc1 = fn.get("doc1line") if isinstance(fn, dict) else None
            if not doc1:
                findings.append({
                    "path": path,
                    "issue": "function_missing_doc",
                    "detail": f"Function '{name}' missing docstring.",
                })

        for cls in entry.get("classes", []):
            # entry['classes'] is list of dicts when using upgraded structure_sync
            if isinstance(cls, dict):
                cname = cls.get("name")
                cdoc1 = cls.get("doc1line")
                if not cdoc1:
                    findings.append({
                        "path": path,
                        "issue": "class_missing_doc",
                        "detail": f"Class '{cname}' missing docstring.",
                    })
                for m in cls.get("methods", []) or []:
                    mname = m.get("name")
                    mdoc1 = m.get("doc1line")
                    if not mdoc1:
                        findings.append({
                            "path": path,
                            "issue": "method_missing_doc",
                            "detail": f"Method '{cname}.{mname}' missing docstring.",
                        })
            else:
                # older snapshot format (class names only)
                cname = str(cls)
                findings.append({
                    "path": path,
                    "issue": "class_missing_doc",
                    "detail": f"Class '{cname}' missing docstring (snapshot lacks details).",
                })

    report: Dict[str, Any] = {
        "meta": {
            "source_snapshot": snapshot_path,
            "total_files_indexed": total_files,
            "python_files": len(py_files),
            "yaml_files": len(yaml_files),
            "markdown_files": len(md_files),
            "loc_thresholds": {"empty_max": LOC_EMPTY_MAX, "large_min": LOC_LARGE_MIN},
        },
        "summary": {
            "files_with_findings": len(set(e["path"] for e in findings)),
            "total_findings": len(findings),
        },
        "findings": findings,
    }

    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        yaml.dump(report, f, allow_unicode=True, sort_keys=False)

    return report

# gui/tabs/plan_tracker_tab.py  (HF1: ctor accepts plan_path or project_config)
# Minimal, robust Plan tab with plan viewer + memory summaries (read-only).
from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QListWidget, QListWidgetItem, QTextEdit, QSplitter
)
from PyQt6.QtCore import Qt
import pathlib, yaml, datetime, os

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEFAULT_PLAN = ROOT / "project" / "plans" / "project_plan_v3.yaml"
MEM_DIR = ROOT / "memory"

def _load_yaml_text(p: pathlib.Path) -> str:
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        # pretty text so we don't depend on yaml view widgets
        return yaml.safe_dump(data, sort_keys=False, allow_unicode=True)
    except Exception as e:
        return f"# ERROR loading YAML: {e}"

def _iter_memory_summaries():
    if not MEM_DIR.exists():
        return []
    out = []
    for p in sorted(MEM_DIR.glob("summary_*.yaml")):
        try:
            with open(p, "r", encoding="utf-8") as f:
                d = yaml.safe_load(f) or {}
            # normalize list-root to dict
            if isinstance(d, list):
                d = {
                    "name": p.stem,
                    "project": "",
                    "date": datetime.datetime.utcnow().isoformat() + "Z",
                    "tokens": 0,
                    "items": d,
                    "tags": [],
                    "preview": ""
                }
            name = d.get("name") or p.stem
            items = d.get("items") or []
            tokens = d.get("tokens") or 0
            tags = d.get("tags") or []
            preview = (d.get("preview") or "")[:400]
            out.append({
                "file": str(p),
                "name": name,
                "items": len(items),
                "tokens": tokens,
                "tags": tags,
                "preview": preview
            })
        except Exception as e:
            out.append({"file": str(p), "name": p.stem, "error": str(e)})
    return out

class PlanTrackerTab(QWidget):
    """
    Plan viewer + Memory summaries (read-only).
    Accepts either:
      - PlanTrackerTab(project_config={'plan_path': '...'})
      - PlanTrackerTab(plan_path='...')
      - or no args (uses default plan path)
    """
    def __init__(self, parent=None, project_config: dict|None=None, plan_path: str|None=None, **_):
        super().__init__(parent)
        # Resolve plan path from args or defaults
        candidate = None
        if isinstance(project_config, dict):
            candidate = project_config.get("plan_path") or candidate
        if plan_path:
            candidate = plan_path
        self.plan_path = pathlib.Path(candidate) if candidate else DEFAULT_PLAN

        self._build_ui()
        self._load_plan()
        self._refresh_memory()

    # --- UI ---
    def _build_ui(self):
        root = QVBoxLayout(self)

        # Top row: plan path + buttons
        top = QHBoxLayout()
        top.addWidget(QLabel("Plan YAML:"))
        self.plan_edit = QLineEdit(str(self.plan_path))
        self.plan_edit.setObjectName("plan_path")
        top.addWidget(self.plan_edit)
        self.btn_refresh = QPushButton("Refresh Plan")
        self.btn_refresh.clicked.connect(self._load_plan)
        top.addWidget(self.btn_refresh)
        root.addLayout(top)

        # Split: left (memory list), right (plan content)
        split = QSplitter(Qt.Orientation.Horizontal)
        left = QWidget(); left_l = QVBoxLayout(left)
        left_l.addWidget(QLabel("Memory Summaries"))
        self.mem_list = QListWidget()
        self.mem_list.itemSelectionChanged.connect(self._show_selected_memory)
        left_l.addWidget(self.mem_list)
        split.addWidget(left)

        right = QWidget(); right_l = QVBoxLayout(right)
        right_l.addWidget(QLabel("Plan YAML (read-only)"))
        self.plan_view = QTextEdit()
        self.plan_view.setReadOnly(True)
        right_l.addWidget(self.plan_view)
        split.addWidget(right)

        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 2)
        root.addWidget(split)

        # Bottom row: small helper actions
        bottom = QHBoxLayout()
        self.btn_reload_mem = QPushButton("Reload Memory")
        self.btn_reload_mem.clicked.connect(self._refresh_memory)
        bottom.addWidget(self.btn_reload_mem)
        bottom.addStretch(1)
        root.addLayout(bottom)

    # --- Behaviors ---
    def _load_plan(self):
        # pick up any edits in the path box
        txt = (self.plan_edit.text() or "").strip()
        if txt:
            self.plan_path = pathlib.Path(txt)
        if not self.plan_path.exists():
            self.plan_view.setPlainText(f"# Plan not found: {self.plan_path}")
            return
        self.plan_view.setPlainText(_load_yaml_text(self.plan_path))

    def _refresh_memory(self):
        self.mem_list.clear()
        rows = _iter_memory_summaries()
        for r in rows:
            if "error" in r:
                item = QListWidgetItem(f"[ERR] {r['file']}  {r['error']}")
                item.setData(Qt.ItemDataRole.UserRole, r)
                self.mem_list.addItem(item)
            else:
                line = f"{r['name']}  ({r['items']} items, tokens={r['tokens']})"
                item = QListWidgetItem(line)
                item.setData(Qt.ItemDataRole.UserRole, r)
                self.mem_list.addItem(item)

    def _show_selected_memory(self):
        items = self.mem_list.selectedItems()
        if not items:
            return
        meta = items[0].data(Qt.ItemDataRole.UserRole) or {}
        if "error" in meta:
            self.plan_view.setPlainText(f"# Memory error\n{meta.get('error')}")
            return
        # Show minimal detail about the selected memory in the plan pane bottom
        preview = meta.get("preview") or ""
        detail = [
            f"# Memory: {meta.get('name','')}",
            f"file: {meta.get('file','')}",
            f"items: {meta.get('items',0)}",
            f"tokens: {meta.get('tokens',0)}",
            f"tags: {meta.get('tags',[])}",
            "",
            preview
        ]
        # Append to existing plan text as a quick contextual view
        current = self.plan_view.toPlainText()
        self.plan_view.setPlainText(current + "\n\n" + "\n".join(detail))

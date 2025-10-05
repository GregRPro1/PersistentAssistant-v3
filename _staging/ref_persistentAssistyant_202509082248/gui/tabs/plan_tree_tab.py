from __future__ import annotations
import pathlib, yaml
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QSplitter, QTreeWidget, QTreeWidgetItem,
    QTextEdit, QLabel
)

ROOT = pathlib.Path(__file__).resolve().parents[2]
PLAN_PATH = ROOT / "project" / "plans" / "project_plan_v3.yaml"

_STATUS_COLOR = {
    "planned": "#888",
    "in_progress": "#e6a700",
    "done": "#2e7d32",
    "blocked": "#c62828",
    None: "#666",
}

def _status_color(s: str) -> str:
    return _STATUS_COLOR.get((s or "").strip(), "#666")

class PlanTreeTab(QWidget):
    """Read-only tree/list view of plan phases/steps with a detail pane."""
    def __init__(self, plan_path: str | None = None, parent=None):
        super().__init__(parent)
        self.plan_path = pathlib.Path(plan_path) if plan_path else PLAN_PATH
        self._init_ui()
        self.refresh()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        self.header = QLabel("Project Plan (Tree)")
        layout.addWidget(self.header)

        self.split = QSplitter(Qt.Orientation.Horizontal, self)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Item", "Status", "ID"])
        self.tree.setColumnWidth(0, 260)
        self.tree.itemSelectionChanged.connect(self._on_select)

        self.detail = QTextEdit()
        self.detail.setReadOnly(True)

        self.split.addWidget(self.tree)
        self.split.addWidget(self.detail)
        self.split.setStretchFactor(0, 3)
        self.split.setStretchFactor(1, 5)

        layout.addWidget(self.split)
        self.setLayout(layout)

    def refresh(self):
        self.tree.clear()
        d = {}
        try:
            with open(self.plan_path, "r", encoding="utf-8") as f:
                d = yaml.safe_load(f) or {}
        except Exception as e:
            self.detail.setPlainText(f"[PlanTree] Failed to load plan: {e}")
            return

        phases = d.get("phases", [])
        for ph in phases:
            pname = ph.get("name") or "Phase"
            pstatus = ph.get("status") or ""
            pitem = QTreeWidgetItem([pname, pstatus, ""])
            pitem.setForeground(1, self._qt_color(_status_color(pstatus)))
            self.tree.addTopLevelItem(pitem)

            for st in ph.get("steps", []) or []:
                sid = st.get("id", "")
                sdesc = st.get("description", f"Step {sid}")
                sstatus = st.get("status") or ""
                it = QTreeWidgetItem([sdesc, sstatus, str(sid)])
                it.setForeground(1, self._qt_color(_status_color(sstatus)))
                pitem.addChild(it)

        self.tree.expandToDepth(1)

    def _on_select(self):
        items = self.tree.selectedItems()
        if not items:
            return
        it = items[0]
        sid = it.text(2).strip()
        txt = [f"Title: {it.text(0)}", f"Status: {it.text(1)}"]
        if sid:
            txt.append(f"ID: {sid}")
        self.detail.setPlainText("\n".join(txt))

    @staticmethod
    def _qt_color(hex_rgb: str):
        from PyQt6.QtGui import QColor, QBrush
        c = QColor(hex_rgb)
        return QBrush(c)

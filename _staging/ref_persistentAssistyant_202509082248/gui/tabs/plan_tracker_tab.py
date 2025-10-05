# gui/tabs/plan_tracker_tab.py — candidate with read-only Memory Viewer section
from __future__ import annotations
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QTextEdit, QMessageBox, QFileDialog
)
from PyQt6.QtCore import Qt, QTimer
import os, subprocess, sys, pathlib, json

# Try to use tools/memory_list.py (works standalone if UI differs upstream)
def list_summaries_json():
    try:
        here = pathlib.Path(__file__).resolve().parents[2]  # project root
        py = sys.executable
        tool = here / "tools" / "memory_list.py"
        if tool.exists():
            p = subprocess.run([py, str(tool), "--as", "json"], capture_output=True, text=True)
            if p.returncode == 0 and p.stdout.strip():
                return json.loads(p.stdout)
    except Exception:
        pass
    return []

class PlanTrackerTab(QWidget):
    """
    Plan tracker with Memory Viewer (read-only).
    NOTE: This is a candidate full-file; guarded replace via safe_replace.py is recommended.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.refresh_memory()

    def init_ui(self):
        lay = QVBoxLayout(self)

        # Existing Plan header
        self.lbl = QLabel("Project Plan & Status")
        self.lbl.setStyleSheet("font-weight: bold;")
        lay.addWidget(self.lbl)

        # Existing plan controls (kept minimal; real upstream may differ)
        btns = QHBoxLayout()
        self.btn_refresh = QPushButton("Refresh Plan")
        self.btn_advance = QPushButton("Advance Step")
        self.btn_rollback = QPushButton("Rollback Step")
        btns.addWidget(self.btn_refresh); btns.addWidget(self.btn_advance); btns.addWidget(self.btn_rollback)
        lay.addLayout(btns)

        # --- Memory Viewer (read-only) ---
        self.mem_label = QLabel("Memory Viewer (read-only)")
        self.mem_label.setStyleSheet("margin-top:12px; font-weight: bold;")
        lay.addWidget(self.mem_label)

        mem_row = QHBoxLayout()
        self.tbl = QTableWidget(0, 5)
        self.tbl.setHorizontalHeaderLabels(["File", "Name", "Items", "Tokens", "Tags"])
        self.tbl.setSelectionBehavior(self.tbl.SelectionBehavior.SelectRows)
        self.tbl.setEditTriggers(self.tbl.EditTrigger.NoEditTriggers)
        self.tbl.cellClicked.connect(self.on_row_clicked)
        mem_row.addWidget(self.tbl, 2)

        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        mem_row.addWidget(self.preview, 3)

        lay.addLayout(mem_row)

        mem_btns = QHBoxLayout()
        self.btn_mem_refresh = QPushButton("Refresh Memory")
        self.btn_open_file = QPushButton("Open File…")
        mem_btns.addWidget(self.btn_mem_refresh); mem_btns.addWidget(self.btn_open_file)
        lay.addLayout(mem_btns)

        self.btn_mem_refresh.clicked.connect(self.refresh_memory)
        self.btn_open_file.clicked.connect(self.open_selected_file)

    def refresh_memory(self):
        rows = list_summaries_json()
        self.tbl.setRowCount(0)
        for r in rows:
            row = self.tbl.rowCount()
            self.tbl.insertRow(row)
            self.tbl.setItem(row, 0, QTableWidgetItem(r.get("file","")))
            self.tbl.setItem(row, 1, QTableWidgetItem(r.get("name","")))
            self.tbl.setItem(row, 2, QTableWidgetItem(str(r.get("items",0))))
            self.tbl.setItem(row, 3, QTableWidgetItem(str(r.get("tokens",0))))
            self.tbl.setItem(row, 4, QTableWidgetItem(", ".join(r.get("tags",[]))))
        if rows:
            self.tbl.selectRow(0); self.on_row_clicked(0,0)
        else:
            self.preview.setPlainText("No memory summaries found. (Run tools/memory_rollup.py)")

    def on_row_clicked(self, r, c):
        file_item = self.tbl.item(r, 0)
        if not file_item: return
        path = file_item.text()
        try:
            import yaml
            with open(path, "r", encoding="utf-8") as f:
                d = yaml.safe_load(f) or {}
            pv = d.get("preview") or ""
            if not pv and d.get("items"):
                # fallback: first few items serialized
                import json
                pv = json.dumps(d.get("items")[:3], ensure_ascii=False, indent=2)
            self.preview.setPlainText(pv or "(no preview)")
        except Exception as e:
            self.preview.setPlainText(f"[ERROR reading {path}] {e}")

    def open_selected_file(self):
        r = self.tbl.currentRow()
        if r < 0: return
        p = self.tbl.item(r, 0).text()
        if not p: return
        try:
            if sys.platform.startswith("win"):
                os.startfile(p)
            else:
                subprocess.Popen(["open" if sys.platform=="darwin" else "xdg-open", p])
        except Exception as e:
            QMessageBox.critical(self, "Open Error", str(e))

#!/usr/bin/env python3
# PAL Tracker — minimal PyQt6 desktop app
# Shows PAL plan progress with dark theme, auto-refreshes every 15s.
# Author: G. Rapson — GR-Analysis

import sys, os, time
from pathlib import Path

REFRESH_SECS = 15
DEFAULT_PLAN_PATH = Path("pal/plan/pal_project_plan.yaml")

# --- YAML loader with graceful fallback ---
def load_yaml(path: Path):
    text = path.read_text(encoding="utf-8")
    try:
        import yaml  # PyYAML
        return yaml.safe_load(text)
    except Exception:
        # Very small fallback parser supporting the structure we ship.
        # It will not handle arbitrary YAML; it is good enough for pal_project_plan.yaml.
        data = {}
        lines = text.splitlines()
        i = 0
        def parse_block(indent=0):
          nonlocal i
          obj = {}
          arr = None
          while i < len(lines):
            raw = lines[i]
            i += 1
            if not raw.strip():
              continue
            cur_indent = len(raw) - len(raw.lstrip())
            if cur_indent < indent:
              i -= 1
              break
            line = raw.strip()
            if line.startswith("- "):
              if arr is None:
                arr = []
              item_line = line[2:]
              if ": " in item_line:
                key, val = item_line.split(": ", 1)
                item = {key: val.strip().strip('"')}
                nested = parse_block(cur_indent + 2)
                if isinstance(nested, dict) and nested:
                  item.update(nested)
                arr.append(item)
              else:
                arr.append(item_line.strip().strip('"'))
            else:
              if ": " in line:
                key, val = line.split(": ", 1)
                if val == "" or val == "|":
                  nested = parse_block(cur_indent + 2)
                  obj[key] = nested
                else:
                  sval = val.strip().strip('"')
                  try:
                    sval_int = int(sval)
                    obj[key] = sval_int
                  except:
                    obj[key] = sval
              elif line.endswith(":"):
                key = line[:-1].strip()
                nested = parse_block(cur_indent + 2)
                obj[key] = nested
              else:
                pass
          return arr if arr is not None else obj
        i = 0
        parsed = parse_block(0)
        return parsed

# --- UI ---
from PyQt6.QtWidgets import (
    QApplication, QWidget, QTreeWidget, QTreeWidgetItem, QTextEdit, QSplitter,
    QVBoxLayout, QLabel, QStatusBar, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPalette, QColor, QFont

STATUS_COLORS = {
    "done": QColor(76, 175, 80),
    "in_progress": QColor(255, 193, 7),
    "review": QColor(0, 188, 212),
    "blocked": QColor(244, 67, 54),
    "todo": QColor(158, 158, 158),
}

def apply_dark_palette(app: QApplication):
    palette = QPalette()
    base = QColor(30,30,30)
    panel = QColor(36,36,36)
    text = QColor(225,225,225)
    accent = QColor(100,149,237)
    palette.setColor(QPalette.ColorRole.Window, panel)
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(45,45,45))
    palette.setColor(QPalette.ColorRole.Base, base)
    palette.setColor(QPalette.ColorRole.Text, text)
    palette.setColor(QPalette.ColorRole.Button, panel)
    palette.setColor(QPalette.ColorRole.ButtonText, text)
    palette.setColor(QPalette.ColorRole.Highlight, accent)
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(0,0,0))
    palette.setColor(QPalette.ColorRole.ToolTipBase, panel)
    palette.setColor(QPalette.ColorRole.ToolTipText, text)
    app.setPalette(palette)

class PalTracker(QWidget):
    def __init__(self, plan_path: Path):
        super().__init__()
        self.plan_path = plan_path
        self.plan = {}
        self.setWindowTitle("PAL Tracker — Persistent Assistant Lite")
        self.resize(1100, 700)
        font = self.font()
        font.setPointSize(10)
        self.setFont(font)

        # Left side: goals + tree
        self.goals_label = QLabel("Goals")
        self.goals_label.setStyleSheet("font-weight:600;")
        self.goals_list = QListWidget()
        self.goals_list.setAlternatingRowColors(True)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["PAL Tasks"])
        self.tree.setAlternatingRowColors(True)
        self.tree.setRootIsDecorated(True)
        self.tree.setColumnCount(1)
        self.tree.setIndentation(18)

        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(8,8,8,8)
        left_layout.setSpacing(6)
        left_layout.addWidget(self.goals_label)
        left_layout.addWidget(self.goals_list, 1)
        left_layout.addWidget(self.tree, 3)

        # Right: details
        self.details = QTextEdit()
        self.details.setReadOnly(True)
        self.details.setStyleSheet("QTextEdit { padding:10px; }")
        self.details.setFont(QFont("Consolas", 10))

        splitter = QSplitter()
        splitter.addWidget(left_container)
        splitter.addWidget(self.details)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        self.status = QStatusBar()
        self.status.showMessage("Loading plan...")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        layout.addWidget(splitter)
        layout.addWidget(self.status)

        self.tree.currentItemChanged.connect(self.on_select_item)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(REFRESH_SECS * 1000)

        self.refresh(initial=True)

    def color_for_status(self, s: str) -> QColor:
        return STATUS_COLORS.get(s or "todo", STATUS_COLORS["todo"])

    def set_item_color(self, item: QTreeWidgetItem, status: str):
        col = self.color_for_status(status)
        item.setForeground(0, col)

    def format_task_summary(self, t: dict) -> str:
        status = t.get("status", "todo")
        pid = t.get("id", "")
        title = t.get("title", "")
        return f"[{status}] {pid} — {title}"

    def default_selection(self):
        root = self.tree.invisibleRootItem()
        in_prog = None
        todo = None
        first = None
        for i in range(root.childCount()):
            ph = root.child(i)
            for j in range(ph.childCount()):
                it = ph.child(j)
                txt = it.text(0)
                if first is None:
                    first = it
                if txt.startswith("[in_progress]"):
                    in_prog = it
                    break
                if txt.startswith("[todo]") and todo is None:
                    todo = it
            if in_prog:
                break
        return in_prog or todo or first

    def rebuild_tree(self):
        self.goals_list.clear()
        self.tree.clear()

        goals = self.plan.get("goals") or []
        for g in goals:
            self.goals_list.addItem(str(g))

        phases = self.plan.get("phases") or []
        for ph in phases:
            ph_item = QTreeWidgetItem([f"{ph.get('id','')}  {ph.get('name','')}"])
            self.set_item_color(ph_item, "todo")
            self.tree.addTopLevelItem(ph_item)
            tasks = ph.get("tasks") or []
            for t in tasks:
                summ = self.format_task_summary(t)
                it = QTreeWidgetItem([summ])
                self.set_item_color(it, t.get("status","todo"))
                it.setData(0, Qt.ItemDataRole.UserRole, (ph, t))
                ph_item.addChild(it)
            ph_item.setExpanded(True)

        sel = self.default_selection()
        if sel:
            self.tree.setCurrentItem(sel)

    def compute_progress(self):
        phases = self.plan.get("phases") or []
        total = 0
        done = 0
        for ph in phases:
            for t in (ph.get("tasks") or []):
                total += 1
                if t.get("status") == "done":
                    done += 1
        pct = int(round((done/total)*100)) if total else 0
        return done, total, pct

    def details_for(self, ph: dict, t: dict) -> str:
        lines = []
        lines.append(f"Phase: {ph.get('id','')} — {ph.get('name','')}")
        lines.append(f"Task: {t.get('id','')}")
        lines.append(f"Title: {t.get('title','')}")
        lines.append(f"Status: {t.get('status','todo')}")
        prio = t.get("priority")
        if prio is not None:
            lines.append(f"Priority: {prio}")
        dod = t.get("dod") or []
        if dod:
            lines.append("DoD:")
            for d in dod:
                lines.append(f"  - {d}")
        for k,v in t.items():
            if k in ("id","title","status","priority","dod"): continue
            lines.append(f"{k}: {v}")
        return "\n".join(lines)

    def on_select_item(self, cur: QTreeWidgetItem, prev: QTreeWidgetItem):
        if not cur:
            self.details.setPlainText("")
            return
        data = cur.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            self.details.setPlainText(cur.text(0))
            return
        ph, t = data
        self.details.setPlainText(self.details_for(ph, t))

    def refresh(self, initial=False):
        try:
            plan_path = self.plan_path
            if not plan_path.exists():
                legacy = Path("project/plans/project_plan_v3.yaml")
                if legacy.exists():
                    plan_path = legacy
                else:
                    self.status.showMessage(f"Plan not found at {self.plan_path}")
                    return
            new = load_yaml(plan_path)
            self.plan = new or {}
            self.rebuild_tree()
            done, total, pct = self.compute_progress()
            self.status.showMessage(f"Overall: {done}/{total} ({pct}%) — refreshed at {time.strftime('%H:%M:%S')}")
        except Exception as e:
            self.status.showMessage(f"Error: {e}")

def main():
    plan_arg = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PLAN_PATH
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    apply_dark_palette(app)
    w = PalTracker(plan_arg)
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

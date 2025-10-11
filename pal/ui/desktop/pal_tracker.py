#!/usr/bin/env python3
import sys, time, socket, threading, json
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QWidget, QTreeWidget, QTreeWidgetItem, QTextEdit, QSplitter,
    QVBoxLayout, QLabel, QStatusBar, QListWidget, QListWidgetItem, QPushButton,
    QHBoxLayout, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QPalette, QColor, QFont

REFRESH_SECS = 15
PING_SECS = 15
DEFAULT_PLAN_PATH = Path("pal/plan/pal_project_plan.yaml")
PING_HOST = "chat.openai.com"; PING_PORT = 443
UI_CONFIG_PATH = Path("pal/config/pal_ui.json")
SMOKE_DIR = Path("reports/smoke")
WATCHER_HEARTBEAT = SMOKE_DIR / "_watcher_heartbeat.txt"

STATUS_COLORS = {
    "done": QColor(76, 175, 80),
    "in_progress": QColor(255, 193, 7),
    "review": QColor(0, 188, 212),
    "blocked": QColor(244, 67, 54),
    "todo": QColor(158, 158, 158),
}

def tcp_ping(host, port, timeout=3.0):
    import socket as s
    try:
        with s.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False

def pick_plan_path() -> Path:
    p1 = Path("pal/plan/pal_project_plan.yaml")
    if p1.exists(): return p1
    p2 = Path("project/plans/project_plan_v3.yaml")
    if p2.exists(): return p2
    return p1

def load_yaml(path: Path):
    txt = path.read_text(encoding="utf-8")
    try:
        import yaml; return yaml.safe_load(txt)
    except Exception:
        lines = txt.splitlines(); i = 0
        def parse_block(indent=0):
            nonlocal i
            obj = {}; arr = None
            while i < len(lines):
                raw = lines[i]; i += 1
                if not raw.strip(): continue
                cur = len(raw) - len(raw.lstrip())
                if cur < indent: i -= 1; break
                line = raw.strip()
                if line.startswith("- "):
                    if arr is None: arr = []
                    tail = line[2:]
                    if ": " in tail:
                        k,v = tail.split(": ",1); item = {k: v.strip().strip('"')}
                        nested = parse_block(cur+2)
                        if isinstance(nested, dict) and nested: item.update(nested)
                        arr.append(item)
                    else:
                        arr.append(tail.strip().strip('"'))
                else:
                    if ": " in line:
                        k,v = line.split(": ",1)
                        if v in ("", "|"):
                            nested = parse_block(cur+2); obj[k] = nested
                        else:
                            sval = v.strip().strip('"')
                            try: obj[k] = int(sval)
                            except: obj[k] = sval
                    elif line.endswith(":"):
                        k = line[:-1].strip(); nested = parse_block(cur+2); obj[k] = nested
            return arr if arr is not None else obj
        i = 0
        return parse_block(0)

def save_yaml(path: Path, data: dict):
    try:
        import yaml
        path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    except Exception:
        pass

def last_smoke_for(task_id: str):
    try:
        p = (SMOKE_DIR / f"{task_id}.json")
        if not p.exists(): return None
        d = json.loads(p.read_text(encoding="utf-8"))
        return {"ok": bool(d.get("ok")), "ts": d.get("ts")}
    except Exception:
        return None

def watcher_on():
    try:
        if not WATCHER_HEARTBEAT.exists(): return False
        age = time.time() - WATCHER_HEARTBEAT.stat().st_mtime
        return age < 20
    except Exception:
        return False

def apply_dark_palette(app: QApplication):
    pal = QPalette()
    base = QColor(30,30,30); panel = QColor(36,36,36); text = QColor(225,225,225); accent = QColor(100,149,237)
    pal.setColor(QPalette.ColorRole.Window, panel)
    pal.setColor(QPalette.ColorRole.AlternateBase, QColor(45,45,45))
    pal.setColor(QPalette.ColorRole.Base, base)
    pal.setColor(QPalette.ColorRole.Text, text)
    pal.setColor(QPalette.ColorRole.Button, panel)
    pal.setColor(QPalette.ColorRole.ButtonText, text)
    pal.setColor(QPalette.ColorRole.Highlight, accent)
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor(0,0,0))
    pal.setColor(QPalette.ColorRole.ToolTipBase, panel)
    pal.setColor(QPalette.ColorRole.ToolTipText, text)
    app.setPalette(pal)

class PingWorker(QObject):
    pingChanged = pyqtSignal(bool)
    def __init__(self, host, port, interval=PING_SECS):
        super().__init__(); self.host=host; self.port=port; self.interval=interval; self._stop=False
    def start(self):
        def run():
            while not self._stop:
                ok = tcp_ping(self.host, self.port, timeout=3.0)
                self.pingChanged.emit(ok)
                for _ in range(int(self.interval*10)):
                    if self._stop: break
                    time.sleep(0.1)
        threading.Thread(target=run, daemon=True).start()
    def stop(self): self._stop=True

class PalTracker(QWidget):
    def __init__(self, plan_path: Path):
        super().__init__(); self.plan_path=plan_path; self.plan={}; self.ping_ok=False
        self.setWindowTitle("PAL Tracker — Persistent Assistant Lite"); self.resize(1100,700)
        f=self.font(); f.setPointSize(10); self.setFont(f)

        self.goals_label = QLabel("Goals"); self.goals_label.setStyleSheet("font-weight:600; color:#e1e1e1;")
        self.goals_list = QListWidget(); self.goals_list.setAlternatingRowColors(True)
        self.tree = QTreeWidget(); self.tree.setHeaderLabels(["PAL Tasks"]); self.tree.setAlternatingRowColors(True)
        self.tree.setRootIsDecorated(True); self.tree.setColumnCount(1); self.tree.setIndentation(18)

        left = QWidget(); lyt = QVBoxLayout(left); lyt.setContentsMargins(8,8,8,8); lyt.setSpacing(6)
        lyt.addWidget(self.goals_label); lyt.addWidget(self.goals_list,1); lyt.addWidget(self.tree,3)

        self.details = QTextEdit(); self.details.setReadOnly(True)
        self.details.setStyleSheet("QTextEdit { padding:10px; color:#e1e1e1; }")
        self.details.setFont(QFont("Consolas", 10))

        self.btnApprove = QPushButton("Approve → Done")
        self.btnReview  = QPushButton("Set Review")
        self.btnInProg  = QPushButton("Set In‑Progress")
        self.btnBlock   = QPushButton("Block")
        for b in (self.btnApprove, self.btnReview, self.btnInProg, self.btnBlock):
            b.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btnApprove.clicked.connect(lambda: self.change_status_selected("done"))
        self.btnReview.clicked.connect(lambda: self.change_status_selected("review"))
        self.btnInProg.clicked.connect(lambda: self.change_status_selected("in_progress"))
        self.btnBlock.clicked.connect(lambda: self.change_status_selected("blocked"))

        actionsRow = QWidget(); from PyQt6.QtWidgets import QHBoxLayout; hb = QHBoxLayout(actionsRow); hb.setContentsMargins(8,4,8,8); hb.setSpacing(8)
        hb.addWidget(self.btnApprove); hb.addWidget(self.btnReview); hb.addWidget(self.btnInProg); hb.addWidget(self.btnBlock); hb.addStretch(1)

        splitter = QSplitter(); splitter.addWidget(left)
        right = QWidget(); from PyQt6.QtWidgets import QVBoxLayout as VB; rv = VB(right); rv.setContentsMargins(0,0,0,0); rv.setSpacing(0)
        rv.addWidget(self.details, 1); rv.addWidget(actionsRow, 0)
        splitter.addWidget(right); splitter.setStretchFactor(0,1); splitter.setStretchFactor(1,2)

        self.status = QStatusBar()
        self.status.setStyleSheet("QStatusBar { background:#242424; color:#e1e1e1; padding:0 6px; } QStatusBar::item { border: 0px; }")
        self.status.setFixedHeight(24)
        small = QFont(self.font()); small.setPointSize(9)
        self.progressLabel = QLabel(""); self.progressLabel.setFont(small); self.progressLabel.setStyleSheet("color:#e1e1e1;")
        self.netLabel = QLabel("OpenAI: …"); self.netLabel.setFont(small); self.netLabel.setStyleSheet("color:#e1e1e1; font-weight:600;")
        self.watchLabel = QLabel("Watcher: …"); self.watchLabel.setFont(small); self.watchLabel.setStyleSheet("color:#b0b0b0;")
        self.timeLabel = QLabel(""); self.timeLabel.setFont(small); self.timeLabel.setStyleSheet("color:#b0b0b0;")
        self.status.addPermanentWidget(self.progressLabel, 2)
        self.status.addPermanentWidget(self.netLabel, 1)
        self.status.addPermanentWidget(self.watchLabel, 1)
        self.status.addPermanentWidget(self.timeLabel, 1)

        v = QVBoxLayout(self); v.setContentsMargins(0,0,0,0); v.addWidget(splitter); v.addWidget(self.status)

        self.tree.currentItemChanged.connect(self.on_select_item)
        self.timer = QTimer(self); self.timer.timeout.connect(self.refresh); self.timer.start(REFRESH_SECS*1000)

        self.ping = PingWorker("chat.openai.com", 443); self.ping.pingChanged.connect(self.on_ping); self.ping.start()

        self.restore_ui_state()
        self.refresh(initial=True)

    def restore_ui_state(self):
        try:
            if UI_CONFIG_PATH.exists():
                cfg = json.loads(UI_CONFIG_PATH.read_text(encoding="utf-8"))
                g = cfg.get("geometry")
                if isinstance(g, list) and len(g)==4: self.setGeometry(*[int(x) for x in g])
        except Exception: pass

    def save_ui_state(self):
        try:
            UI_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            r = self.geometry()
            cfg = {"geometry": [int(r.x()), int(r.y()), int(r.width()), int(r.height())]}
            UI_CONFIG_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
        except Exception: pass

    def closeEvent(self, event):
        self.save_ui_state()
        super().closeEvent(event)

    def on_ping(self, ok: bool):
        self.ping_ok = ok; self.update_status_bar()

    def color_for_status(self, s: str): return STATUS_COLORS.get(s or "todo", STATUS_COLORS["todo"])
    def set_item_color(self, item: QTreeWidgetItem, status: str):
        item.setForeground(0, self.color_for_status(status))
        try:
            from PyQt6.QtGui import QFont
            f = item.font(0); f.setBold(True if status=='in_progress' else False); item.setFont(0, f)
        except Exception: pass

    def format_task_summary(self, t: dict) -> str:
        return f"[{t.get('status','todo')}] {t.get('id','')} — {t.get('title','')}"

    def default_selection(self):
        root = self.tree.invisibleRootItem(); ip=None; todo=None; first=None
        for i in range(root.childCount()):
            ph = root.child(i)
            for j in range(ph.childCount()):
                it = ph.child(j); txt = it.text(0)
                if first is None: first = it
                if txt.startswith("[in_progress]"): ip = it; break
                if txt.startswith("[review]") and not ip: ip = it
                if txt.startswith("[todo]") and todo is None: todo = it
            if ip: break
        return ip or todo or first

    def rebuild_tree(self):
        self.goals_list.clear(); self.tree.clear()
        for g in (self.plan.get("goals") or []): QListWidgetItem(str(g), self.goals_list)
        for ph in (self.plan.get("phases") or []):
            ph_item = QTreeWidgetItem([f"{ph.get('id','')}  {ph.get('name','')}"]); self.set_item_color(ph_item,"todo"); self.tree.addTopLevelItem(ph_item)
            for t in (ph.get("tasks") or []):
                it = QTreeWidgetItem([self.format_task_summary(t)]); self.set_item_color(it, t.get("status","todo")); it.setData(0, Qt.ItemDataRole.UserRole, (ph,t)); ph_item.addChild(it)
            ph_item.setExpanded(True)
        sel = self.default_selection(); 
        if sel: self.tree.setCurrentItem(sel)

    def compute_progress(self):
        total=0; done=0
        for ph in (self.plan.get("phases") or []):
            for t in (ph.get("tasks") or []):
                total+=1; done+= 1 if t.get("status")=='done' else 0
        pct=int(round((done/total)*100)) if total else 0
        return done,total,pct

    def last_smoke_for(self, task_id: str):
        try:
            p = Path("reports/smoke") / f"{task_id}.json"
            if not p.exists(): return None
            d = json.loads(p.read_text(encoding="utf-8"))
            return {"ok": bool(d.get("ok")), "ts": d.get("ts")}
        except Exception: return None

    def details_for(self, ph: dict, t: dict) -> str:
        lines = [f"Phase: {ph.get('id','')} — {ph.get('name','')}",
                 f"Task: {t.get('id','')}", f"Title: {t.get('title','')}",
                 f"Status: {t.get('status','todo')}"]
        pr = t.get('priority'); 
        if pr is not None: lines.append(f"Priority: {pr}")
        sm = self.last_smoke_for(str(t.get("id","")))
        if sm:
            lines.append(f"Last smoke: {'PASS' if sm['ok'] else 'FAIL'} @ {sm.get('ts','?')}")
        dod = t.get('dod') or []
        if dod:
            lines.append("DoD:"); [lines.append(f"  - {d}") for d in dod]
        for k,v in t.items():
            if k in ("id","title","status","priority","dod"): continue
            lines.append(f"{k}: {v}")
        return "\n".join(lines)

    def on_select_item(self, cur, prev):
        if not cur: self.details.setPlainText(""); return
        data = cur.data(0, Qt.ItemDataRole.UserRole)
        if not data: self.details.setPlainText(cur.text(0)); self.update_action_buttons(None,None); return
        ph,t = data; self.details.setPlainText(self.details_for(ph,t)); self.update_action_buttons(ph,t)

    def update_action_buttons(self, ph, t):
        if not t:
            for b in (self.btnApprove, self.btnReview, self.btnInProg, self.btnBlock): b.setEnabled(False)
            return
        s = t.get("status","todo")
        self.btnApprove.setEnabled(s in ("review","in_progress"))
        self.btnReview.setEnabled(s in ("in_progress","blocked"))
        self.btnInProg.setEnabled(s in ("todo","review","blocked"))
        self.btnBlock.setEnabled(s in ("todo","in_progress","review"))

    def update_status_bar(self):
        d,t,p = self.compute_progress()
        self.progressLabel.setText(f"Overall: {d}/{t} ({p}%)")
        if self.ping_ok:
            self.netLabel.setText("OpenAI: OK"); self.netLabel.setStyleSheet("color:#4CAF50; font-weight:700;")
        else:
            self.netLabel.setText("OpenAI: FAIL"); self.netLabel.setStyleSheet("color:#F44336; font-weight:700;")
        # watcher
        hb = Path("reports/smoke/_watcher_heartbeat.txt")
        try:
            on = hb.exists() and (time.time() - hb.stat().st_mtime) < 20
        except Exception: on = False
        if on:
            self.watchLabel.setText("Watcher: ON"); self.watchLabel.setStyleSheet("color:#4CAF50; font-weight:600;")
        else:
            self.watchLabel.setText("Watcher: OFF"); self.watchLabel.setStyleSheet("color:#F44336; font-weight:600;")
        self.timeLabel.setText(time.strftime("%H:%M:%S"))

    def change_status_selected(self, new_status: str):
        item = self.tree.currentItem()
        if not item: return
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data: return
        ph,t = data
        tid = str(t.get("id",""))
        try:
            plan_path = pick_plan_path()
            plan = load_yaml(plan_path) or {}
            for ph2 in plan.get("phases", []):
                for tt in ph2.get("tasks", []):
                    if str(tt.get("id")) == tid:
                        tt["status"] = new_status
            save_yaml(plan_path, plan)
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to change status: {e}")

    def refresh(self, initial=False):
        try:
            plan_path = self.plan_path if self.plan_path.exists() else pick_plan_path()
            if not plan_path.exists(): self.progressLabel.setText("Plan not found"); return
            self.plan = load_yaml(plan_path) or {}
            self.rebuild_tree(); self.update_status_bar()
        except Exception as e:
            self.progressLabel.setText(f"Error: {e}")

def main():
    plan = Path(sys.argv[1]) if len(sys.argv)>1 else pick_plan_path()
    app = QApplication(sys.argv); apply_dark_palette(app)
    w = PalTracker(plan); w.show(); sys.exit(app.exec())

if __name__=="__main__": main()

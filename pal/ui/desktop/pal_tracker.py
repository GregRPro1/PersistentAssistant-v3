#!/usr/bin/env python3
import sys, time, socket, threading, json
from pathlib import Path
from PyQt6.QtWidgets import (QApplication, QWidget, QTreeWidget, QTreeWidgetItem, QTextEdit, QSplitter, QVBoxLayout, QLabel, QStatusBar, QListWidget, QListWidgetItem)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QPalette, QColor, QFont

REFRESH_SECS = 15
PING_SECS = 15
DEFAULT_PLAN_PATH = Path("pal/plan/pal_project_plan.yaml")
PING_HOST = "chat.openai.com"; PING_PORT = 443
UI_CONFIG_PATH = Path("pal/config/pal_ui.json")

def tcp_ping(host, port, timeout=3.0):
    import socket as s
    try:
        with s.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False

def load_yaml(path: Path):
    text = path.read_text(encoding="utf-8")
    try:
        import yaml; return yaml.safe_load(text)
    except Exception:
        lines = text.splitlines(); i=0
        def parse_block(indent=0):
            nonlocal i; obj={}; arr=None
            while i < len(lines):
                raw = lines[i]; i+=1
                if not raw.strip(): continue
                cur=len(raw)-len(raw.lstrip())
                if cur < indent: i-=1; break
                line=raw.strip()
                if line.startswith("- "):
                    if arr is None: arr=[]
                    tail=line[2:]
                    if ": " in tail:
                        k,v=tail.split(": ",1); item={k:v.strip().strip('"')}
                        nested = parse_block(cur+2)
                        if isinstance(nested, dict) and nested: item.update(nested)
                        arr.append(item)
                    else:
                        arr.append(tail.strip().strip('"'))
                else:
                    if ": " in line:
                        k,v=line.split(": ",1)
                        if v in ("", "|"):
                            nested = parse_block(cur+2); obj[k]=nested
                        else:
                            sval=v.strip().strip('"')
                            try: obj[k]=int(sval)
                            except: obj[k]=sval
                    elif line.endswith(":"):
                        k=line[:-1].strip(); nested=parse_block(cur+2); obj[k]=nested
            return arr if arr is not None else obj
        i=0; return parse_block(0)

STATUS_COLORS = {"done": QColor(76,175,80), "in_progress": QColor(255,193,7), "review": QColor(0,188,212), "blocked": QColor(244,67,54), "todo": QColor(158,158,158)}

def apply_dark_palette(app):
    pal=QPalette(); base=QColor(30,30,30); panel=QColor(36,36,36); text=QColor(225,225,225); accent=QColor(100,149,237)
    pal.setColor(QPalette.ColorRole.Window, panel); pal.setColor(QPalette.ColorRole.AlternateBase, QColor(45,45,45)); pal.setColor(QPalette.ColorRole.Base, base)
    pal.setColor(QPalette.ColorRole.Text, text); pal.setColor(QPalette.ColorRole.Button, panel); pal.setColor(QPalette.ColorRole.ButtonText, text)
    pal.setColor(QPalette.ColorRole.Highlight, accent); pal.setColor(QPalette.ColorRole.HighlightedText, QColor(0,0,0))
    pal.setColor(QPalette.ColorRole.ToolTipBase, panel); pal.setColor(QPalette.ColorRole.ToolTipText, text); app.setPalette(pal)

class PingWorker(QObject):
    pingChanged = pyqtSignal(bool)
    def __init__(self, host, port, interval=PING_SECS): super().__init__(); self.host=host; self.port=port; self.interval=interval; self._stop=False
    def start(self):
        def run():
            while not self._stop:
                ok = tcp_ping(self.host, self.port, timeout=3.0); self.pingChanged.emit(ok)
                for _ in range(int(self.interval*10)):
                    if self._stop: break; time.sleep(0.1)
        threading.Thread(target=run, daemon=True).start()
    def stop(self): self._stop=True

class PalTracker(QWidget):
    def __init__(self, plan_path: Path):
        super().__init__(); self.plan_path=plan_path; self.plan={}; self.ping_ok=False
        self.setWindowTitle("PAL Tracker — Persistent Assistant Lite"); self.resize(1100,680)
        f=self.font(); f.setPointSize(10); self.setFont(f)
        self.goals_label=QLabel("Goals"); self.goals_label.setStyleSheet("font-weight:600; color:#e1e1e1;")
        self.goals_list=QListWidget(); self.goals_list.setAlternatingRowColors(True)
        self.tree=QTreeWidget(); self.tree.setHeaderLabels(["PAL Tasks"]); self.tree.setAlternatingRowColors(True); self.tree.setRootIsDecorated(True); self.tree.setColumnCount(1); self.tree.setIndentation(18)
        left=QWidget(); from PyQt6.QtWidgets import QVBoxLayout; l=QVBoxLayout(left); l.setContentsMargins(8,8,8,4); l.setSpacing(6); l.addWidget(self.goals_label); l.addWidget(self.goals_list,1); l.addWidget(self.tree,3)
        self.details=QTextEdit(); self.details.setReadOnly(True); self.details.setStyleSheet("QTextEdit { padding:8px; color:#e1e1e1; }"); self.details.setFont(QFont("Consolas",10))

        self.splitter=QSplitter(); self.splitter.addWidget(left); self.splitter.addWidget(self.details); self.splitter.setStretchFactor(0,1); self.splitter.setStretchFactor(1,2)

        self.status=QStatusBar(); self.status.setSizeGripEnabled(False)
        self.status.setStyleSheet("QStatusBar { background:#242424; color:#e1e1e1; padding:0 6px; } QStatusBar::item { border: 0px; }")
        self.status.setFixedHeight(24)
        small = QFont(self.font()); small.setPointSize(9)
        self.progressLabel=QLabel(""); self.progressLabel.setFont(small); self.progressLabel.setStyleSheet("color:#e1e1e1;")
        self.netLabel=QLabel("OpenAI: …"); self.netLabel.setFont(small); self.netLabel.setStyleSheet("color:#e1e1e1; font-weight:600;")
        self.timeLabel=QLabel(""); self.timeLabel.setFont(small); self.timeLabel.setStyleSheet("color:#b0b0b0;")
        self.status.addPermanentWidget(self.progressLabel,2); self.status.addPermanentWidget(self.netLabel,1); self.status.addPermanentWidget(self.timeLabel,1)

        v=QVBoxLayout(self); v.setContentsMargins(0,0,0,0); v.setSpacing(0); v.addWidget(self.splitter); v.addWidget(self.status)

        self.tree.currentItemChanged.connect(self.on_select_item)
        self.timer=QTimer(self); self.timer.timeout.connect(self.refresh); self.timer.start(REFRESH_SECS*1000)
        self.ping=PingWorker("chat.openai.com",443); self.ping.pingChanged.connect(self.on_ping); self.ping.start()

        self.restore_ui_state()

        # Debounced autosave of geometry on move/resize every 2s after changes
        self._geom_dirty = False
        self._geom_timer = QTimer(self); self._geom_timer.setSingleShot(True); self._geom_timer.timeout.connect(self.save_ui_state)

        self.refresh(initial=True)

    # ---- UI state persistence ----
    def restore_ui_state(self):
        try:
            if UI_CONFIG_PATH.exists():
                cfg = json.loads(UI_CONFIG_PATH.read_text(encoding="utf-8"))
                g = cfg.get("geometry"); sp = cfg.get("splitter")
                if isinstance(g, list) and len(g)==4:
                    self.setGeometry(int(g[0]), int(g[1]), int(g[2]), int(g[3]))
                if isinstance(sp, list) and len(sp)>=2:
                    self.splitter.setSizes([int(sp[0]), int(sp[1])])
        except Exception:
            pass

    def save_ui_state(self):
        try:
            UI_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            r = self.geometry()
            cfg = {
                "geometry": [int(r.x()), int(r.y()), int(r.width()), int(r.height())],
                "splitter": self.splitter.sizes()
            }
            UI_CONFIG_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
        except Exception:
            pass

    def moveEvent(self, event):
        self._geom_timer.start(2000)  # debounce 2s
        return super().moveEvent(event)

    def resizeEvent(self, event):
        self._geom_timer.start(2000)  # debounce 2s
        return super().resizeEvent(event)

    def closeEvent(self, event):
        self.save_ui_state()
        return super().closeEvent(event)

    # ---- core ----
    def on_ping(self, ok: bool):
        self.ping_ok=ok; self.update_status_bar()
    def color_for_status(self,s): return STATUS_COLORS.get(s or "todo", STATUS_COLORS["todo"])
    def set_item_color(self,it,status):
        it.setForeground(0, self.color_for_status(status))
        try:
            from PyQt6.QtGui import QFont
            f = it.font(0); f.setBold(True if status=='in_progress' else False); it.setFont(0, f)
        except Exception:
            pass
    def format_task_summary(self,t): return f"[{t.get('status','todo')}] {t.get('id','')} — {t.get('title','')}"
    def default_selection(self):
        root=self.tree.invisibleRootItem(); ip=None; td=None; first=None
        for i in range(root.childCount()):
            ph=root.child(i)
            for j in range(ph.childCount()):
                it=ph.child(j); txt=it.text(0)
                if first is None: first=it
                if txt.startswith("[in_progress]"): ip=it; break
                if txt.startswith("[todo]") and td is None: td=it
            if ip: break
        return ip or td or first
    def rebuild_tree(self):
        self.goals_list.clear(); self.tree.clear()
        for g in (self.plan.get("goals") or []): QListWidgetItem(str(g), self.goals_list)
        for ph in (self.plan.get("phases") or []):
            ph_item=QTreeWidgetItem([f"{ph.get('id','')}  {ph.get('name','')}"]); self.set_item_color(ph_item,"todo"); self.tree.addTopLevelItem(ph_item)
            for t in (ph.get("tasks") or []):
                it=QTreeWidgetItem([self.format_task_summary(t)]); self.set_item_color(it, t.get("status","todo")); it.setData(0, Qt.ItemDataRole.UserRole, (ph,t)); ph_item.addChild(it)
            ph_item.setExpanded(True)
        sel=self.default_selection(); 
        if sel: self.tree.setCurrentItem(sel)
    def compute_progress(self):
        total=0; done=0
        for ph in (self.plan.get("phases") or []):
            for t in (ph.get("tasks") or []):
                total+=1; done+= 1 if t.get("status")=='done' else 0
        pct=int(round((done/total)*100)) if total else 0
        return done,total,pct
    def details_for(self,ph,t):
        ls=[f"Phase: {ph.get('id','')} — {ph.get('name','')}", f"Task: {t.get('id','')}", f"Title: {t.get('title','')}", f"Status: {t.get('status','todo')}"]
        pr=t.get('priority'); 
        if pr is not None: ls.append(f"Priority: {pr}")
        dod=t.get('dod') or []
        if dod:
            ls.append("DoD:"); [ls.append(f"  - {d}") for d in dod]
        for k,v in t.items():
            if k in ("id","title","status","priority","dod"): continue
            ls.append(f"{k}: {v}")
        return "\n".join(ls)
    def on_select_item(self, cur, prev):
        if not cur: self.details.setPlainText(""); return
        data = cur.data(0, Qt.ItemDataRole.UserRole)
        if not data: self.details.setPlainText(cur.text(0)); return
        ph,t = data; self.details.setPlainText(self.details_for(ph,t))
    def update_status_bar(self):
        d,t,p = self.compute_progress()
        self.progressLabel.setText(f"Overall: {d}/{t} ({p}%)")
        if self.ping_ok:
            self.netLabel.setText("OpenAI: OK"); self.netLabel.setStyleSheet("color:#4CAF50; font-weight:700;")
        else:
            self.netLabel.setText("OpenAI: FAIL"); self.netLabel.setStyleSheet("color:#F44336; font-weight:700;")
        self.timeLabel.setText(time.strftime("%H:%M:%S"))
    def refresh(self, initial=False):
        try:
            plan_path = self.plan_path if self.plan_path.exists() else Path("project/plans/project_plan_v3.yaml")
            if not plan_path.exists(): self.progressLabel.setText("Plan not found"); return
            self.plan = load_yaml(plan_path) or {}
            self.rebuild_tree(); self.update_status_bar()
        except Exception as e:
            self.progressLabel.setText(f"Error: {e}")

def main():
    plan = Path(sys.argv[1]) if len(sys.argv)>1 else DEFAULT_PLAN_PATH
    app = QApplication(sys.argv); apply_dark_palette(app); w=PalTracker(plan); w.show(); sys.exit(app.exec())
if __name__=="__main__": main()

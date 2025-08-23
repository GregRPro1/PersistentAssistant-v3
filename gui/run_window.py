from __future__ import annotations
import json, pathlib, subprocess, sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLineEdit, QTextEdit, QLabel, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt

ROOT = pathlib.Path(__file__).resolve().parents[1]

class RunWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Persistent Assistant – Run")
        self._init_ui()

    def _init_ui(self):
        lay = QVBoxLayout(self)

        self.cmdEdit = QLineEdit("python tools/show_next_step.py")
        lay.addWidget(QLabel("Command:"))
        lay.addWidget(self.cmdEdit)

        btnRow = QHBoxLayout()
        self.btnRun = QPushButton("Run")
        self.btnOpenLogs = QPushButton("Open LEB Logs Folder")
        btnRow.addWidget(self.btnRun)
        btnRow.addWidget(self.btnOpenLogs)
        lay.addLayout(btnRow)

        self.out = QTextEdit()
        self.out.setReadOnly(True)
        lay.addWidget(QLabel("Output:"))
        lay.addWidget(self.out)

        self.btnRun.clicked.connect(self.on_run)
        self.btnOpenLogs.clicked.connect(self.on_open_logs)

    def on_open_logs(self):
        logs = ROOT.parent/"logs"/"leb"
        logs.mkdir(parents=True, exist_ok=True)
        try:
            QFileDialog.getOpenFileName(self, "LEB Logs", str(logs))
        except Exception:
            QMessageBox.information(self, "Logs", str(logs))

    def on_run(self):
        cmd = self.cmdEdit.text().strip()
        if not cmd:
            return
        try:
            p = subprocess.run([sys.executable, str(ROOT/"tools"/"leb_runner.py"), "--", cmd],
                               capture_output=True, text=True)
            text = p.stdout + ("\n" + p.stderr if p.stderr else "")
            self.out.clear()
            self.out.append(text)
            try:
                data = json.loads(p.stdout.strip())
                if not data.get("ok"):
                    self.out.append("\n[LEB] command failed.")
            except Exception:
                pass
        except Exception as e:
            QMessageBox.critical(self, "Run error", str(e))

def main():
    app = QApplication(sys.argv)
    w = RunWindow()
    w.resize(900, 600)
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

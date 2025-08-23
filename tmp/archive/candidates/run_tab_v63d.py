# gui/tabs/run_tab.py (v63d)
# Final wiring: Ping/Run/Logs + Auto-refresh + Start/Stop server
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QLineEdit, QTextEdit, QCheckBox, QMessageBox)
from PyQt6.QtCore import QTimer
import subprocess, sys, os, json, traceback

# Root import (so "core" resolves when launched from different cwd)
import pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from core.leb_client import LEBClient
except Exception as e:
    LEBClient = None

class RunTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._proc = None
        self._timer = QTimer(self)
        self._timer.setInterval(1500)
        self._timer.timeout.connect(self.on_refresh_logs)
        self.init_ui()

    def init_ui(self):
        lay = QVBoxLayout(self)

        row = QHBoxLayout()
        self.btn_ping = QPushButton("Ping LEB")
        self.btn_run  = QPushButton("Run")
        self.btn_logs = QPushButton("Refresh Logs")
        self.chk_auto = QCheckBox("Auto-refresh")
        row.addWidget(self.btn_ping); row.addWidget(self.btn_run)
        row.addWidget(self.btn_logs); row.addWidget(self.chk_auto)
        lay.addLayout(row)

        srow = QHBoxLayout()
        self.btn_start = QPushButton("Start Server")
        self.btn_stop  = QPushButton("Stop Server")
        srow.addWidget(self.btn_start); srow.addWidget(self.btn_stop)
        lay.addLayout(srow)

        self.cmd = QLineEdit("python --version")
        self.out = QTextEdit()
        self.out.setReadOnly(True)
        lay.addWidget(QLabel("Command:"))
        lay.addWidget(self.cmd)
        lay.addWidget(QLabel("Output:"))
        lay.addWidget(self.out)

        self.btn_ping.clicked.connect(self.on_ping)
        self.btn_run.clicked.connect(self.on_run)
        self.btn_logs.clicked.connect(self.on_refresh_logs)
        self.chk_auto.toggled.connect(self.on_auto_toggle)
        self.btn_start.clicked.connect(self.on_start)
        self.btn_stop.clicked.connect(self.on_stop)

    # ----- helpers
    def _client(self):
        if LEBClient is None:
            raise RuntimeError("LEBClient unavailable")
        return LEBClient()

    def _append(self, text):
        self.out.append(text)

    def _show_err(self, title, exc: Exception):
        # first line of stack for quick triage
        tb = traceback.format_exc().splitlines()
        head = tb[-1] if tb else str(exc)
        QMessageBox.critical(self, title, f"{exc}\n\n{head}")

    # ----- actions
    def on_ping(self):
        try:
            c = self._client()
            res = c.ping()
            self._append(json.dumps(res, indent=2))
        except Exception as e:
            self._show_err("LEB Ping Error", e)

    def on_run(self):
        try:
            c = self._client()
            cmd = (self.cmd.text() or "").strip()
            if not cmd:
                QMessageBox.information(self, "Run", "Please enter a command.")
                return
            res = c.run(cmd)
            self._append(json.dumps(res, indent=2))
        except Exception as e:
            self._show_err("LEB Run Error", e)

    def on_refresh_logs(self):
        try:
            c = self._client()
            res = c.logs()
            self._append(json.dumps(res, indent=2))
        except Exception as e:
            self._show_err("LEB Logs Error", e)

    def on_auto_toggle(self, enabled):
        if enabled:
            self._timer.start()
        else:
            self._timer.stop()

    def on_start(self):
        try:
            # Spawn: python tools\leb_server.py
            server = os.path.join(str(ROOT), "tools", "leb_server.py")
            if not os.path.exists(server):
                raise FileNotFoundError(server)
            # Use a detached process so GUI stays responsive
            creationflags = 0
            if os.name == "nt":
                creationflags = subprocess.CREATE_NEW_CONSOLE
            self._proc = subprocess.Popen(
                [sys.executable, server],
                cwd=str(ROOT),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creationflags
            )
            QMessageBox.information(self, "LEB", "Server launch attempted.")
        except Exception as e:
            self._show_err("LEB Start Error", e)

    def on_stop(self):
        try:
            if self._proc and self._proc.poll() is None:
                self._proc.terminate()
                self._proc = None
                QMessageBox.information(self, "LEB", "Server stop signalled.")
            else:
                QMessageBox.information(self, "LEB", "No tracked server process.")
        except Exception as e:
            self._show_err("LEB Stop Error", e)

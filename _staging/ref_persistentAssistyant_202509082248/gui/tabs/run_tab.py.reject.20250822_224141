# gui/tabs/run_tab.py
# Run tab: send commands to Local Exec Bridge, view results and logs
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTextEdit
from PyQt6.QtCore import QTimer
import traceback

class RunTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._setup_timer()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        row = QHBoxLayout()
        row.addWidget(QLabel("Command:"))
        self.cmd_edit = QLineEdit("python --version")
        row.addWidget(self.cmd_edit)

        self.btn_ping = QPushButton("Ping LEB")
        self.btn_run  = QPushButton("Run")
        self.btn_logs = QPushButton("Refresh Logs")

        row.addWidget(self.btn_ping)
        row.addWidget(self.btn_run)
        row.addWidget(self.btn_logs)
        layout.addLayout(row)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        layout.addWidget(self.output)

        self.btn_ping.clicked.connect(self.on_ping)
        self.btn_run.clicked.connect(self.on_run)
        self.btn_logs.clicked.connect(self.on_logs)

    def _setup_timer(self):
        # Optional auto-refresh later; off by default
        self._timer = QTimer(self)
        self._timer.setInterval(2000)
        self._timer.timeout.connect(self.on_logs)

    def _append(self, text: str):
        self.output.append(text)

    def _client(self):
        from core.leb_client import LEBClient
        return LEBClient()

    def on_ping(self):
        try:
            data = self._client().ping()
            self._append(f"[PING] {data}")
        except Exception as e:
            self._append("[PING ERROR] " + str(e) + "\n" + traceback.format_exc().splitlines()[-1])

    def on_run(self):
        try:
            cmd = (self.cmd_edit.text() or "").strip()
            if not cmd:
                self._append("[RUN] No command provided.")
                return
            data = self._client().run(cmd)
            self._append("[RUN] " + str(data))
        except Exception as e:
            self._append("[RUN ERROR] " + str(e) + "\n" + traceback.format_exc().splitlines()[-1])

    def on_logs(self):
        try:
            data = self._client().logs()
            self._append("[LOGS] " + str(data))
        except Exception as e:
            self._append("[LOGS ERROR] " + str(e) + "\n" + traceback.format_exc().splitlines()[-1])

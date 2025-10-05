from __future__ import annotations

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QTextEdit
from PyQt6.QtCore import QTimer
import json, os, glob

class RunTab(QWidget):
    """
    Minimal Run tab (v1):
      - Task selector (predefined safe tasks)
      - Run/Stop buttons
      - Log viewer (polls latest logs/leb/run_*.log)
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._log_timer = QTimer(self)
        self._log_timer.setInterval(1000)
        self._log_timer.timeout.connect(self._refresh_log)
        self._current_log = None

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        top = QHBoxLayout()
        layout.addLayout(top)

        top.addWidget(QLabel("Task:"))
        self.task = QComboBox()
        # Predefined safe tasks (no network writes, just local tools)
        self.task.addItems([
            "Probe models (tools\\probe_models.py)",
            "Run unit tests (tools\\run_tests.py)",
            "Sanitize project YAML (tools\\sanitize_project_yaml.py)",
            "Export insights (tools\\export_insights.py)"
        ])
        top.addWidget(self.task)

        self.btn_run = QPushButton("Run")
        self.btn_stop = QPushButton("Stop")
        top.addWidget(self.btn_run)
        top.addWidget(self.btn_stop)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(QLabel("Output (latest):"))
        layout.addWidget(self.log)

        self.btn_run.clicked.connect(self._on_run)
        self.btn_stop.clicked.connect(self._on_stop)

    def _latest_log(self):
        files = glob.glob(os.path.join("logs","leb","run_*.log"))
        if not files:
            return None
        return max(files, key=os.path.getmtime)

    def _refresh_log(self):
        latest = self._latest_log()
        if latest and latest != self._current_log:
            self._current_log = latest
        if self._current_log and os.path.exists(self._current_log):
            try:
                with open(self._current_log, "r", encoding="utf-8", errors="ignore") as f:
                    self.log.setPlainText(f.read()[-20000:])
            except Exception as e:
                self.log.setPlainText(f"[ERROR reading log] {e}")

    def _on_run(self):
        task = self.task.currentText()
        if "Probe models" in task:
            cmd = "python tools\\probe_models.py"
        elif "Run unit tests" in task:
            cmd = "python tools\\run_tests.py"
        elif "Sanitize project YAML" in task:
            cmd = "python tools\\sanitize_project_yaml.py"
        elif "Export insights" in task:
            cmd = "python tools\\export_insights.py"
        else:
            cmd = "python -V"
        # dispatch via LEB client
        import subprocess, sys
        p = subprocess.run([sys.executable, "tools\\leb_client.py", cmd], capture_output=True, text=True)
        # start tailing latest
        self._log_timer.start()
        self._refresh_log()

    def _on_stop(self):
        # v1: no long-run kill; just stop polling
        self._log_timer.stop()

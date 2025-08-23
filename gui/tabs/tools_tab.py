# =============================================================================
# File: gui/tabs/tools_tab.py
# Persistent Assistant v3 – Tools Tab (streamed runner + summaries + visible status)
# Author: G. Rapson | GR-Analysis
# Created: 2025-08-19
# Created-Time: 2025-08-19 11:55 BST
# AtCreation:
#   line_count: 420   # informational; actual counts logged at runtime
#   function_count: 19
# Update History:
#   - 2025-08-19 11:55 BST: Switch to QProcess (non-blocking), live PROGRESS parsing,
#       JSON SUMMARY capture, per-run logs, PYTHONPATH enforcement, status mirrored.
# =============================================================================

from __future__ import annotations

import os
import sys
import ast
import json
import logging
import datetime
from typing import Optional, Tuple, List, Dict, Any

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QMessageBox
)
from PyQt6.QtCore import Qt, QProcess, QByteArray
from PyQt6.QtGui import QGuiApplication, QCursor

# Centralized key/env helper
try:
    from tools._env import build_env, load_keys, mask_key
except Exception:
    def build_env(base=None):  # type: ignore
        import os as _os
        return dict(base or _os.environ)
    def load_keys(): return {}
    def mask_key(k): return "MISSING"

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")


class ToolsTab(QWidget):
    """
    Operational tools tab that runs project tools asynchronously via QProcess.

    Features:
      - Live, non-blocking execution with “running…/completed” status.
      - Status mirrored to the main window status bar.
      - Buttons disabled during runs and re-enabled on completion.
      - Per-run log file for every execution under logs/.
      - Streaming parsing of lines:
          * PROGRESS: {"n":1,"m":10,"ok":1,"fail":0,"skipped":0,"label":"openai/gpt-4o-mini"}
          * SUMMARY:  {...final machine-readable summary...}
    """

    # ------------------------------ Construction ------------------------------ #
    def __init__(self, controller, parent: Optional[QWidget] = None):
        """
        Args:
            controller: MainWindow instance exposing hooks for GUI-only actions:
                - apply_prompt_formatting()
                - dummy_ai_send()
                - copy_all_as_yaml()
                - run_structure_snapshot()
                - run_introspection_report()
                - create_improvement_tasks()
        """
        super().__init__(parent)
        self.controller = controller
        self._init_logger()
        self._init_ui()
        self._log_runtime_meta()

        # QProcess state
        self._proc: Optional[QProcess] = None
        self._run_log_path: str = ""
        self._last_summary: Dict[str, Any] = {}
        self._pipeline: List[Tuple[List[str], Dict[str, str], str]] = []  # (cmd, env, label)
        self._current_step_label: str = ""

    # ------------------------------ UI setup --------------------------------- #
    def _init_ui(self) -> None:
        """
        Build rows:
          1) Prompt utilities
          2) Analysis & tasks
          3) Model catalogue ops, diagnostics, logs
        """
        root = QVBoxLayout()

        # Row 1 — prompt utilities
        row1 = QHBoxLayout()
        row1.addWidget(self._mk_ctrl_btn("Format Prompt", "apply_prompt_formatting"))
        row1.addWidget(self._mk_ctrl_btn("Send to AI (Simulated)", "dummy_ai_send"))
        row1.addWidget(self._mk_ctrl_btn("Copy All as YAML", "copy_all_as_yaml"))
        root.addLayout(row1)

        # Row 2 — analysis & tasks
        row2 = QHBoxLayout()
        row2.addWidget(self._mk_ctrl_btn("Run Structure Snapshot", "run_structure_snapshot"))
        row2.addWidget(self._mk_ctrl_btn("Generate Introspection Report", "run_introspection_report"))
        row2.addWidget(self._mk_ctrl_btn("Create Improvement Tasks", "create_improvement_tasks"))
        root.addLayout(row2)

        # Row 3 — model ops + diagnostics + logs
        row3 = QHBoxLayout()

        self.btn_update_models = QPushButton("Update AI Models Catalogue")
        self.btn_update_models.clicked.connect(self._on_update_ai_models)
        row3.addWidget(self.btn_update_models)

        self.btn_probe = QPushButton("Probe Models (Ping)")
        self.btn_probe.clicked.connect(self._on_probe_models)
        row3.addWidget(self.btn_probe)

        self.btn_check_keys = QPushButton("Check API Keys")
        self.btn_check_keys.clicked.connect(lambda: self._run_tool_single(["tools/check_api_keys.py"],
                                                                          title="Check API keys"))
        row3.addWidget(self.btn_check_keys)

        self.btn_selfcheck = QPushButton("Verify Tools Wiring")
        self.btn_selfcheck.clicked.connect(lambda: self._run_tool_single(["tools/self_check.py"],
                                                                         title="Verify tools wiring"))
        row3.addWidget(self.btn_selfcheck)

        self.btn_open_logs = QPushButton("Open Logs Folder")
        self.btn_open_logs.clicked.connect(self._on_open_logs)
        row3.addWidget(self.btn_open_logs)

        root.addLayout(row3)

        # Persistent status (mirrored to status bar)
        self.status_label = QLabel("Ready.")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.status_label.setWordWrap(True)
        self.status_label.setMinimumHeight(36)
        root.addWidget(self.status_label)

        self.setLayout(root)

        # Track buttons for enable/disable
        self._all_buttons: List[QPushButton] = [w for w in self.findChildren(QPushButton)]

    def _mk_ctrl_btn(self, text: str, handler_name: str) -> QPushButton:
        """
        Create a button wired to a controller method if available.

        Returns:
            QPushButton (disabled with tooltip if the hook is missing).
        """
        btn = QPushButton(text)
        fn = getattr(self.controller, handler_name, None)
        if callable(fn):
            btn.clicked.connect(fn)  # type: ignore[arg-type]
        else:
            btn.setDisabled(True)
            btn.setToolTip(f"Missing controller hook: {handler_name}")
            self.logger.warning("Controller missing hook: %s", handler_name)
        return btn

    # ------------------------------ Logging/Status --------------------------- #
    def _init_logger(self) -> None:
        """Initialize logger and ensure logs dir exists."""
        os.makedirs(LOG_DIR, exist_ok=True)
        logging.basicConfig(
            filename=os.path.join(LOG_DIR, "persistent_assistant.log"),
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            encoding="utf-8"
        )
        self.logger = logging.getLogger("PersistentAssistant.ToolsTab")

    def _emit_status(self, text: str) -> None:
        """
        Update the Tools tab label, mirror to main status bar, and log it.
        """
        self.status_label.setText(text)
        try:
            if hasattr(self.controller, "status") and self.controller.status:
                self.controller.status.showMessage(text)
        except Exception:
            pass
        try:
            self.logger.info(text)
        except Exception:
            pass

    def _set_busy(self, msg: str) -> None:
        """
        Enter 'busy' state: show message, disable buttons, set wait cursor.
        """
        self._emit_status(msg)
        for b in self._all_buttons:
            b.setEnabled(False)
        QGuiApplication.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor))

    def _clear_busy(self, msg: str) -> None:
        """
        Exit 'busy' state: re-enable buttons, restore cursor, show completion message.
        """
        for b in self._all_buttons:
            b.setEnabled(True)
        QGuiApplication.restoreOverrideCursor()
        self._emit_status(msg)

    def _log_runtime_meta(self) -> None:
        """
        Log actual line/function counts for this file (audit aid).
        """
        try:
            self_path = os.path.abspath(__file__)
            with open(self_path, "r", encoding="utf-8") as f:
                src = f.read()
            line_count = src.count("\n") + 1
            fn_count = sum(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) for n in ast.walk(ast.parse(src)))
            self.logger.info("META tools_tab.py: lines=%s functions=%s", line_count, fn_count)
        except Exception:
            pass

    # ------------------------------ QProcess Runner -------------------------- #
    def _build_env(self, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """
        Build environment for subprocess, injecting API keys and PYTHONPATH.
        """
        env = build_env(os.environ.copy())
        if extra:
            env.update(extra)
        # Ensure Python finds 'tools' as a package in subprocess
        old_pp = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = PROJECT_ROOT + (os.pathsep + old_pp if old_pp else "")
        # Force UTF-8 IO for consistent logs
        env.setdefault("PYTHONIOENCODING", "utf-8")
        return env

    def _make_run_log_path(self, cmd: List[str]) -> str:
        """
        Create a unique per-run log path for command.
        """
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        safe = "_".join(cmd).replace("\\", "_").replace("/", "_")
        return os.path.join(LOG_DIR, f"tool_run_{safe}_{ts}.log")

    def _start_process(self, cmd: List[str], title: str, env_extra: Optional[Dict[str, str]] = None) -> None:
        """
        Start QProcess for the given tool command.

        Stream handling:
          - Each stdout line appended to run log.
          - Lines starting with 'PROGRESS:' update the status live.
          - 'SUMMARY:' is captured for final dialog.

        On finish:
          - Buttons re-enabled, status updated, dialog presented.
        """
        # Close any previous process cleanly
        if self._proc and self._proc.state() != QProcess.ProcessState.NotRunning:
            try:
                self._proc.kill()
            except Exception:
                pass

        self._proc = QProcess(self)
        self._current_step_label = title
        self._last_summary = {}
        self._run_log_path = self._make_run_log_path(cmd)

        env = self._build_env(env_extra)
        # Prepare process
        self._proc.setProgram(sys.executable)
        self._proc.setWorkingDirectory(PROJECT_ROOT)
        self._proc.setArguments(cmd)
        self._proc.setProcessEnvironment(self._qprocess_env(env))

        # Connect signals
        self._proc.readyReadStandardOutput.connect(self._on_stdout)
        self._proc.readyReadStandardError.connect(self._on_stderr)
        self._proc.finished.connect(self._on_finished)

        # Initial log header
        self._write_log_header(cmd, env)

        # UI state
        self._set_busy(f"{title} running… please wait (see: {self._run_log_path})")

        # Start
        self._proc.start()

    def _qprocess_env(self, env_dict: Dict[str, str]):
        """
        Convert dict to QProcessEnvironment (done lazily here to avoid GUI import mismatch).
        """
        from PyQt6.QtCore import QProcessEnvironment
        pe = QProcessEnvironment.systemEnvironment()
        for k, v in env_dict.items():
            pe.insert(k, v)
        return pe

    def _write_log_header(self, cmd: List[str], env: Dict[str, str]) -> None:
        """
        Write a header with masked keys and target script meta.
        """
        os.makedirs(LOG_DIR, exist_ok=True)
        keys = load_keys()
        masked = {k: mask_key(v) for k, v in (keys or {}).items()}
        try:
            with open(self._run_log_path, "w", encoding="utf-8") as f:
                f.write(f"CWD: {PROJECT_ROOT}\n")
                f.write(f"CMD: {sys.executable} {' '.join(cmd)}\n")
                f.write(f"ENV_KEYS: {masked}\n")
                # Target meta
                target = os.path.join(PROJECT_ROOT, cmd[0])
                try:
                    with open(target, "r", encoding="utf-8") as sf:
                        src = sf.read()
                    import ast
                    line_count = src.count("\n") + 1
                    fn_count = sum(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) for n in ast.walk(ast.parse(src)))
                    f.write(f"META: file={cmd[0]} lines={line_count} functions={fn_count}\n")
                except Exception:
                    pass
                f.write("---- STREAM ----\n")
        except Exception:
            pass

    def _append_log(self, text: str) -> None:
        """Append a line to the current run log (best-effort)."""
        try:
            with open(self._run_log_path, "a", encoding="utf-8") as f:
                f.write(text)
                if not text.endswith("\n"):
                    f.write("\n")
        except Exception:
            pass

    def _on_stdout(self) -> None:
        """
        Handle streaming stdout: capture PROGRESS and SUMMARY lines.
        """
        if not self._proc:
            return
        data: QByteArray = self._proc.readAllStandardOutput()
        chunk = bytes(data).decode("utf-8", errors="replace")
        for raw_line in chunk.splitlines():
            line = raw_line.strip()
            self._append_log(line)
            if line.startswith("PROGRESS:"):
                # Live progress JSON
                try:
                    prog = json.loads(line[len("PROGRESS:"):].strip())
                    n = prog.get("n"); m = prog.get("m")
                    ok = prog.get("ok", 0); fail = prog.get("fail", 0)
                    skipped = prog.get("skipped", 0)
                    label = prog.get("label", "")
                    self._emit_status(f"{self._current_step_label}… {n}/{m} • ok:{ok} fail:{fail} skip:{skipped} • {label}")
                except Exception:
                    pass
            elif line.startswith("SUMMARY:"):
                try:
                    self._last_summary = json.loads(line[len("SUMMARY:"):].strip())
                except Exception:
                    self._last_summary = {}

    def _on_stderr(self) -> None:
        """
        Append stderr to the log and show a brief status hint (without popping dialogs).
        """
        if not self._proc:
            return
        data: QByteArray = self._proc.readAllStandardError()
        chunk = bytes(data).decode("utf-8", errors="replace")
        for raw_line in chunk.splitlines():
            line = raw_line.rstrip()
            self._append_log("[stderr] " + line)
        # Keep UI quiet; final dialog will summarize

    def _on_finished(self, exit_code: int, exit_status) -> None:
        """
        Handle process completion: re-enable UI, show dialog with parsed SUMMARY (if present).
        """
        title = self._current_step_label or "Tool"
        ok = (exit_code == 0)
        if ok:
            self._clear_busy(f"{title} completed. Log: {self._run_log_path}")
            pretty = json.dumps(self._last_summary, indent=2) if self._last_summary else "Done."
            QMessageBox.information(self, f"{title} – Summary", f"{pretty}\n\nLog:\n{self._run_log_path}")
        else:
            self._clear_busy(f"{title} failed (rc={exit_code}). Log: {self._run_log_path}")
            msg = self._last_summary or {"error": "See log"}
            QMessageBox.warning(self, f"{title} – Failed",
                                f"{json.dumps(msg, indent=2)}\n\nLog:\n{self._run_log_path}")

        # If running a pipeline, continue with next step
        if self._pipeline:
            self._start_next_pipeline_step()

    # ------------------------------ High-level actions ----------------------- #
    def _on_update_ai_models(self) -> None:
        """
        Run the 3-step AI models pipeline with live status:
          1) fetch_ai_models.py
          2) update_ai_models.py (enrich; emits SUMMARY)
          3) check_ai_models.py ai_models.yaml (final validity)
        """
        self._pipeline = [
            (["tools/fetch_ai_models.py"], {}, "AI Models: fetch (RAW)"),
            (["tools/update_ai_models.py"], {"PA_ENRICH_DEBUG": "1"}, "AI Models: enrich/merge"),
            (["tools/check_ai_models.py", "ai_models.yaml"], {}, "AI Models: final check"),
        ]
        self._last_summary = {}
        self._start_next_pipeline_step()

    def _start_next_pipeline_step(self) -> None:
        """
        Start the next pipeline step if present; otherwise clear the queue.
        """
        if not self._pipeline:
            self._pipeline = []
            return
        cmd, envx, label = self._pipeline.pop(0)
        self._start_process(cmd, title=label, env_extra=envx)

    def _on_probe_models(self) -> None:
        """
        Run the model probe with live PROGRESS (per model).
        """
        self._run_tool_single(["tools/probe_models.py"], title="Probe models")

    def _run_tool_single(self, cmd: List[str], title: str) -> None:
        """
        Convenience wrapper to run a single tool with streaming behavior.
        """
        self._start_process(cmd, title=title)

    def _on_open_logs(self) -> None:
        """
        Open the logs directory in the system file explorer.
        """
        path = os.path.abspath(LOG_DIR)
        try:
            if os.name == "nt":
                os.startfile(path)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                import subprocess as sp; sp.run(["open", path])
            else:
                import subprocess as sp; sp.run(["xdg-open", path])
        except Exception as e:
            QMessageBox.warning(self, "Open Logs Failed", f"Could not open:\n{path}\n\n{e}")

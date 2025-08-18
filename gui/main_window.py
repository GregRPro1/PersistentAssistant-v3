# main_window.py
# Persistent Assistant v3
# Created: 2025-08-18
# Author: G. Rapson
# Company: GR-Analysis
# Description:
#   Defines the MainWindow class which contains the tabbed interface
#   for raw input, prompt formatting, AI response, and plan tracking.

from PyQt6.QtWidgets import QMainWindow, QTabWidget, QPushButton, QVBoxLayout, QWidget, QApplication, QLabel
from PyQt6.QtWidgets import QStatusBar, QMenuBar, QMenu, QMessageBox
from PyQt6.QtGui import QAction

from PyQt6.QtCore import QTimer
from gui.tabs.input_tab import InputTab
from gui.tabs.prompt_tab import PromptTab
from gui.tabs.response_tab import ResponseTab
from gui.tabs.plan_tracker_tab import PlanTrackerTab
from gui.tabs.chat_tab import ChatTab
from core.prompt_formatter import format_prompt
from core.introspection import generate_introspection_report
from core.tasks import create_tasks_from_introspection
from core.project_session import load_project_config, save_session, make_default_session
from gui.dialogs.project_selector import ProjectSelectorDialog


# New: for Copy-All-as-YAML and Structure Snapshot
import os
import yaml
import datetime
import subprocess
import sys

from core.logger import get_logger

print(f"Interpreter: {sys.executable}")

class MainWindow(QMainWindow):
    """
    Main window of the Persistent Assistant application.

    Provides a tabbed interface containing:
    - Raw user input (InputTab)
    - Formatted prompt output (PromptTab)
    - AI response display (ResponseTab)
    - Project plan tracker (PlanTrackerTab)
    - Embedded Chat tab
    - Tools tab (temporary) with workflow helpers
    """
    def __init__(self, project_session: dict | None = None):
        super().__init__()
        self.logger = getattr(self, "logger", None) or (get_logger("gui") if "get_logger" in globals() else None)


        self.setWindowTitle("Persistent Assistant v3")
        self.project_session = project_session or {}

        # Merge project config (paths, plan)
        self.project_config = load_project_config(self.project_session)

        # Status bar shows project info
        self.status = QStatusBar(self)
        self.setStatusBar(self.status)
        self._refresh_status_bar()



        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)

        # Initialize and add all tabs
        self.input_tab = InputTab()
        self.prompt_tab = PromptTab()
        self.response_tab = ResponseTab(
            input_tab=self.input_tab,
            prompt_tab=self.prompt_tab
        )
        self.plan_tracker_tab = PlanTrackerTab(plan_path=self.project_config.get("plan_path"))
        self.chat_tab = ChatTab()

        self.tab_widget.addTab(self.input_tab, "Input")
        self.tab_widget.addTab(self.prompt_tab, "Prompt")
        self.tab_widget.addTab(self.response_tab, "Response")
        self.tab_widget.addTab(self.plan_tracker_tab, "Plan")
        self.tab_widget.addTab(self.chat_tab, "Chat")

        # Menubar
        self._build_menu()

        # Tools tab (temporary): format, simulated send, copy all as YAML, structure snapshot
        control_widget = QWidget()
        control_layout = QVBoxLayout()

        self.format_button = QPushButton("Format Prompt")
        self.format_button.clicked.connect(self.apply_prompt_formatting)
        control_layout.addWidget(self.format_button)

        self.send_button = QPushButton("Send to AI (Simulated)")
        self.send_button.clicked.connect(self.dummy_ai_send)
        control_layout.addWidget(self.send_button)

        self.copy_all_button = QPushButton("Copy All as YAML")
        self.copy_all_button.clicked.connect(self.copy_all_as_yaml)
        control_layout.addWidget(self.copy_all_button)

        self.snapshot_button = QPushButton("Run Structure Snapshot")
        self.snapshot_button.clicked.connect(self.run_structure_snapshot)
        control_layout.addWidget(self.snapshot_button)

        self.introspect_button = QPushButton("Generate Introspection Report")
        self.introspect_button.clicked.connect(self.run_introspection_report)
        control_layout.addWidget(self.introspect_button)

        self.tasks_button = QPushButton("Create Improvement Tasks")
        self.tasks_button.clicked.connect(self.create_improvement_tasks)
        control_layout.addWidget(self.tasks_button)

        self.tools_status = QLabel("")
        control_layout.addWidget(self.tools_status)

        control_widget.setLayout(control_layout)
        self.tab_widget.addTab(control_widget, "Tools")

        self.resize(1000, 700)

    def _refresh_status_bar(self):
        name = self.project_config.get("project_name", "(unnamed)")
        root = self.project_config.get("project_root", "(root?)")
        plan = self.project_config.get("plan_path", "(plan?)")
        self.status.showMessage(f"Project: {name} • Root: {root} • Plan: {plan}")


    def apply_prompt_formatting(self):
        """
        Reads raw input, applies formatting logic, and updates the prompt tab.
        """
        raw_input = self.input_tab.get_input_text()
        formatted_prompt = format_prompt(raw_input)
        self.prompt_tab.set_prompt_text(formatted_prompt)

    def dummy_ai_send(self):
        """
        Simulates sending the prompt to an AI system by copying prompt text to response tab.
        """
        prompt_text = self.prompt_tab.get_prompt_text()
        self.response_tab.set_response_text(f"[Simulated AI Response]\n\n{prompt_text}")

    # --- Step 1.12: Copy All as YAML ---
    def copy_all_as_yaml(self):
        """
        Collects input, prompt, and response text; writes a timestamped YAML file
        to data/interactions, and copies the YAML text to the system clipboard.
        Also shows a status message on the Response tab.
        """
        input_text = self.input_tab.get_input_text()
        prompt_text = self.prompt_tab.get_prompt_text()
        response_text = self.response_tab.get_response_text()

        # Prepare YAML payload
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        payload = {
            "development_stage": "1.12 of 16 to achieve MVP",
            "timestamp": ts,
            "source": "gui-clipboard",
            "input_text": input_text,
            "prompt_text": prompt_text,
            "response_text": response_text,
        }

        yaml_text = yaml.dump(payload, allow_unicode=True, sort_keys=False)

        # Write to file
        log_dir = os.path.join("data", "interactions")
        os.makedirs(log_dir, exist_ok=True)
        filepath = os.path.join(log_dir, f"interaction_{ts}_all.yaml")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(yaml_text)

        # Copy to clipboard
        QApplication.clipboard().setText(yaml_text)

        # Status feedback via Response tab (non-modal)
        if hasattr(self.response_tab, "status_label"):
            self.response_tab.status_label.setText(f"Saved combined YAML and copied to clipboard: {filepath}")
            QTimer.singleShot(5000, lambda: self.response_tab.status_label.setText(""))

    # --- Step 1.15: Run Structure Snapshot ---
    def run_structure_snapshot(self):
        """
        Runs tools/structure_sync.py with the current interpreter, logs all output,
        and shows a concise status in the Tools tab.
        """
        try:
            self.tools_status.setText("Running structure snapshot…")
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            cmd = [sys.executable, "tools/structure_sync.py"]
            env = dict(os.environ)
            env.setdefault("PYTHONIOENCODING", "utf-8")

            result = subprocess.run(cmd, capture_output=True, text=True, check=False, env=env)
            stdout = (result.stdout or "").strip()
            stderr = (result.stderr or "").strip()

            # Write a per-run detailed log
            os.makedirs("logs", exist_ok=True)
            run_log_path = os.path.join("logs", f"structure_sync_run_{ts}.log")
            with open(run_log_path, "w", encoding="utf-8") as f:
                f.write(f"Command: {cmd}\nReturn code: {result.returncode}\n\n")
                if stdout:
                    f.write("---- STDOUT ----\n")
                    f.write(stdout + "\n\n")
                if stderr:
                    f.write("---- STDERR ----\n")
                    f.write(stderr + "\n")

            # Summarize for app.log
            if result.returncode == 0:
                msg = f"Structure snapshot OK. See {run_log_path}"
                self.logger.info(msg)
                # Show concise success in UI (keep visible longer)
                ui_msg = stdout if stdout else "✅ Snapshot complete."
                self.tools_status.setText(ui_msg)
                # Clear after 12s (success)
                QTimer.singleShot(12000, lambda: self.tools_status.setText(""))
            else:
                msg = f"Structure snapshot FAILED rc={result.returncode}. See {run_log_path}"
                self.logger.error(msg)
                if stderr:
                    self.logger.error(f"stderr: {stderr}")
                # Show error summary in UI and DO NOT auto-clear
                self.tools_status.setText(f"❌ Snapshot failed (rc={result.returncode}). See logs/app.log")
        except Exception as e:
            # Log unexpected exceptions
            self.logger.exception(f"Exception in run_structure_snapshot: {e}")
            self.tools_status.setText(f"❌ Error: {e}. See logs/app.log")

    def run_introspection_report(self):
        """
        Generates the introspection report from the latest structure snapshot.
        Writes to data/insights/introspection_report.yaml and reports status.
        """
        try:
            report = generate_introspection_report()
            issues = report.get("summary", {}).get("files_with_findings", 0)
            total = report.get("summary", {}).get("total_findings", 0)
            msg = f"Introspection OK: {issues} files with findings, {total} findings. See data/insights/introspection_report.yaml"
            if hasattr(self, "tools_status") and self.tools_status:
                self.tools_status.setText(msg)
                QTimer.singleShot(12000, lambda: self.tools_status.setText(""))
            if getattr(self, "logger", None):
                self.logger.info(msg)
        except Exception as e:
            err = f"Introspection FAILED: {e}"
            if hasattr(self, "tools_status") and self.tools_status:
                self.tools_status.setText(err)   # leave visible for manual copy
            if getattr(self, "logger", None):
                self.logger.exception(err)

    def create_improvement_tasks(self):
        """
        Generates task YAMLs from the latest introspection report.
        Writes data/tickets/task_*.yaml and updates data/tickets/index.yaml.
        """
        try:
            summary = create_tasks_from_introspection()
            msg = (f"Created {summary['created']} tasks "
                f"(files affected: {summary['files_affected']}). "
                f"Index: {summary['index_path']}")
            if hasattr(self, "tools_status") and self.tools_status:
                self.tools_status.setText(msg)
                QTimer.singleShot(12000, lambda: self.tools_status.setText(""))
            # Optional: if you wired a central logger earlier
            try:
                self.logger.info(msg)
            except Exception:
                pass
        except Exception as e:
            err = f"❌ Task generation failed: {e}"
            if hasattr(self, "tools_status") and self.tools_status:
                self.tools_status.setText(err)   # leave visible for manual copy
            try:
                self.logger.exception(err)
            except Exception:
                pass

    def _build_menu(self):
        mb = self.menuBar() if self.menuBar() else QMenuBar(self)
        self.setMenuBar(mb)

        proj_menu = mb.addMenu("Project")

        act_switch = QAction("Switch…", self)
        act_switch.triggered.connect(self.switch_project)
        proj_menu.addAction(act_switch)

    def _refresh_status_bar(self):
        name = self.project_config.get("project_name", "(unnamed)")
        root = self.project_config.get("project_root", "(root?)")
        plan = self.project_config.get("plan_path", "(plan?)")
        self.status.showMessage(f"Project: {name} • Root: {root} • Plan: {plan}")

    def switch_project(self):
        """
        Open the project selector dialog, save the session, reload config,
        update Plan tab and status bar.
        """
        # Pre-fill dialog with current values
        defaults = {
            "project_name": self.project_config.get("project_name", "Persistent Assistant v3"),
            "project_root": self.project_config.get("project_root", ""),
            "plan_path":    self.project_config.get("plan_path", ""),
        }

        dlg = ProjectSelectorDialog(defaults, self)
        from PyQt6.QtWidgets import QDialog
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        new_session = dlg.session_data()
        try:
            save_session(new_session)
            # Reload merged config
            self.project_session = new_session
            self.project_config = load_project_config(self.project_session)
            # Update Plan tab and status bar
            self.plan_tracker_tab.set_plan_path(self.project_config.get("plan_path", "project/plans/project_plan_v3.yaml"))
            self._refresh_status_bar()
            QMessageBox.information(self, "Project switched",
                                    "Project session saved and configuration reloaded.")
        except Exception as e:
            QMessageBox.critical(self, "Switch failed", f"Could not switch project:\n{e}")


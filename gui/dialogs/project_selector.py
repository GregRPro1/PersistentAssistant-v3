# project_selector.py
# Persistent Assistant v3
# Created: 2025-08-18
# Author: G. Rapson
# Company: GR-Analysis
# Description:
#   Simple dialog to select project name, root path, and plan path. Persists to session.

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog
)
from PyQt6.QtCore import Qt
import os

class ProjectSelectorDialog(QDialog):
    """
    Minimal project selector dialog.
    """
    def __init__(self, defaults: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Project")
        self.defaults = defaults
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout()

        # Project name
        layout.addWidget(QLabel("Project name:"))
        self.name_edit = QLineEdit(self.defaults.get("project_name", ""))
        layout.addWidget(self.name_edit)

        # Project root
        layout.addWidget(QLabel("Project root:"))
        root_row = QHBoxLayout()
        self.root_edit = QLineEdit(self.defaults.get("project_root", ""))
        browse_root = QPushButton("Browse…")
        browse_root.clicked.connect(self._browse_root)
        root_row.addWidget(self.root_edit)
        root_row.addWidget(browse_root)
        layout.addLayout(root_row)

        # Plan path
        layout.addWidget(QLabel("Plan path (YAML):"))
        plan_row = QHBoxLayout()
        self.plan_edit = QLineEdit(self.defaults.get("plan_path", ""))
        browse_plan = QPushButton("Browse…")
        browse_plan.clicked.connect(self._browse_plan)
        plan_row.addWidget(self.plan_edit)
        plan_row.addWidget(browse_plan)
        layout.addLayout(plan_row)

        # Buttons
        btn_row = QHBoxLayout()
        save_btn = QPushButton("Save")
        cancel_btn = QPushButton("Cancel")
        save_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(save_btn)
        btn_row.addWidget(cancel_btn)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)

        self.setLayout(layout)
        self.setModal(True)
        self.resize(600, 200)

    def _browse_root(self):
        path = QFileDialog.getExistingDirectory(self, "Select Project Root", self.root_edit.text() or os.getcwd())
        if path:
            self.root_edit.setText(path)

    def _browse_plan(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Plan YAML", self.plan_edit.text() or os.getcwd(), "YAML Files (*.yaml *.yml)")
        if path:
            self.plan_edit.setText(path)

    def session_data(self) -> dict:
        return {
            "project_name": self.name_edit.text().strip(),
            "project_root": self.root_edit.text().strip(),
            "plan_path": self.plan_edit.text().strip(),
        }

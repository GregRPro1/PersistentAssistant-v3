# plan_tracker_tab.py
# Persistent Assistant v3
# Created: 2025-08-18
# Author: G. Rapson
# Company: GR-Analysis
# Description:
#   Defines the PlanTrackerTab class, which will display the active project
#   development plan derived from the master tracker YAML file.

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel

class PlanTrackerTab(QWidget):
    """
    A Qt tab that will display the stepwise development plan of the project.

    Initially a placeholder. Future versions will load and display the
    contents of project_plan.yaml as a table or tree.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        """
        Initializes the layout for the PlanTrackerTab.
        """
        layout = QVBoxLayout()

        label = QLabel("Plan Tracker (coming soon)")
        layout.addWidget(label)

        self.setLayout(layout)

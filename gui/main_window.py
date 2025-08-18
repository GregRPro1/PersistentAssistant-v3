# main_window.py
# Persistent Assistant v3
# Created: 2025-08-18
# Author: G. Rapson
# Company: GR-Analysis
# Description:
#   Defines the MainWindow class which contains the tabbed interface
#   for raw input, prompt formatting, AI response, and plan tracking.

from PyQt6.QtWidgets import QMainWindow, QTabWidget
from gui.tabs.input_tab import InputTab
from gui.tabs.prompt_tab import PromptTab
from gui.tabs.response_tab import ResponseTab
from gui.tabs.plan_tracker_tab import PlanTrackerTab

class MainWindow(QMainWindow):
    """
    Main window of the Persistent Assistant application.

    Provides a tabbed interface containing:
    - Raw user input (InputTab)
    - Formatted prompt output (PromptTab)
    - AI response display (ResponseTab)
    - Project plan tracker (PlanTrackerTab)
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Persistent Assistant v3")

        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)

        # Initialize and add all tabs
        self.input_tab = InputTab()
        self.prompt_tab = PromptTab()
        self.response_tab = ResponseTab()
        self.plan_tracker_tab = PlanTrackerTab()

        self.tab_widget.addTab(self.input_tab, "Input")
        self.tab_widget.addTab(self.prompt_tab, "Prompt")
        self.tab_widget.addTab(self.response_tab, "Response")
        self.tab_widget.addTab(self.plan_tracker_tab, "Plan")

        self.resize(1000, 700)

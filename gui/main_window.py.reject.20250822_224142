# gui/main_window.py
# Minimal guarded version that wires RunTab. Keep your existing imports/other tabs if needed.
from PyQt6.QtWidgets import QMainWindow, QWidget, QTabWidget
from gui.tabs.run_tab import RunTab

class MainWindow(QMainWindow):
    def __init__(self, project_session=None, project_config=None):
        super().__init__()
        self.setWindowTitle("Persistent Assistant v3")
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Existing tabs would also be added here in your full file.
        # Ensure Run tab:
        self.run_tab = RunTab(self)
        self.tabs.addTab(self.run_tab, "Run")

# main.py
# Persistent Assistant v3
# Created: 2025-08-18
# Author: G. Rapson
# Company: GR-Analysis
# Description:
#   Entry point for the Persistent Assistant Qt application.
#   Initializes the main window and starts the application loop.

import sys
from PyQt6.QtWidgets import QApplication
from gui.main_window import MainWindow

def main():
    """
    Launches the Persistent Assistant Qt application.
    """
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

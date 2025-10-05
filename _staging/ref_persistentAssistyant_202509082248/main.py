# main.py
# Persistent Assistant v3
# Created: 2025-08-18
# Author: G. Rapson
# Company: GR-Analysis
# Description:
#   App entry point. Ensures a project session exists before launching main window.

import sys
from PyQt6.QtWidgets import QApplication, QDialog
from gui.main_window import MainWindow
from core.project_session import load_session, save_session, make_default_session
from gui.dialogs.project_selector import ProjectSelectorDialog

def main():
    app = QApplication(sys.argv)

    # Ensure we have a valid session
    session = load_session()
    if session is None:
        defaults = make_default_session()
        dlg = ProjectSelectorDialog(defaults)
        # PyQt6: use QDialog.DialogCode.Accepted
        if dlg.exec() == QDialog.DialogCode.Accepted:
            session = dlg.session_data()
            save_session(session)
        else:
            sys.exit(0)

    window = MainWindow(project_session=session)
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

# input_tab.py
# Persistent Assistant v3
# Created: 2025-08-18
# Author: G. Rapson
# Company: GR-Analysis
# Description:
#   Defines the InputTab class which provides a multi-line text editor
#   for raw user input that will later be formatted into structured prompts.
#   Adds clipboard copy support with confirmation label.

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit, QPushButton, QApplication
from PyQt6.QtCore import QTimer

class InputTab(QWidget):
    """
    A Qt tab that provides a multiline text editor for raw user input.

    This input can later be used to generate AI prompts or be directly submitted.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.status_label = QLabel("")
        self.init_ui()

    def init_ui(self):
        """
        Initializes the user interface layout for the InputTab.
        """
        layout = QVBoxLayout()

        self.label = QLabel("Enter raw input below:")
        layout.addWidget(self.label)

        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("Type your prompt or notes here...")
        layout.addWidget(self.text_edit)

        self.copy_button = QPushButton("Copy to Clipboard")
        self.copy_button.clicked.connect(self.copy_to_clipboard)
        layout.addWidget(self.copy_button)

        layout.addWidget(self.status_label)
        self.setLayout(layout)

    def get_input_text(self) -> str:
        """
        Returns the current content of the text editor.

        Returns:
            str: The user's input text.
        """
        return self.text_edit.toPlainText()

    def copy_to_clipboard(self):
        """
        Copies the current input text to the clipboard and shows confirmation.
        """
        clipboard = QApplication.clipboard()
        clipboard.setText(self.get_input_text())
        self.status_label.setText("Copied input to clipboard.")
        QTimer.singleShot(3000, lambda: self.status_label.setText(""))

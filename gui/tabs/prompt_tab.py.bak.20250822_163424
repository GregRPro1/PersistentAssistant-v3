# prompt_tab.py
# Persistent Assistant v3
# Created: 2025-08-18
# Author: G. Rapson
# Company: GR-Analysis
# Description:
#   Defines the PromptTab class which displays a formatted version
#   of the user input. Supports editable prompt preview, clipboard copy, and status feedback.

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit, QPushButton, QApplication
from PyQt6.QtCore import QTimer

class PromptTab(QWidget):
    """
    A Qt tab that displays the formatted prompt derived from raw user input.

    The prompt text can be edited before being submitted to the AI model.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.status_label = QLabel("")
        self.init_ui()

    def init_ui(self):
        """
        Initializes the user interface layout for the PromptTab.
        """
        layout = QVBoxLayout()

        self.label = QLabel("Formatted Prompt (editable):")
        layout.addWidget(self.label)

        self.prompt_edit = QTextEdit()
        self.prompt_edit.setPlaceholderText("Formatted version of input will appear here...")
        layout.addWidget(self.prompt_edit)

        self.copy_button = QPushButton("Copy to Clipboard")
        self.copy_button.clicked.connect(self.copy_to_clipboard)
        layout.addWidget(self.copy_button)

        layout.addWidget(self.status_label)
        self.setLayout(layout)

    def get_prompt_text(self) -> str:
        """
        Returns the current prompt content.

        Returns:
            str: The formatted prompt text.
        """
        return self.prompt_edit.toPlainText()

    def set_prompt_text(self, text: str):
        """
        Sets the content of the prompt editor.

        Args:
            text (str): The formatted prompt.
        """
        self.prompt_edit.setPlainText(text)

    def copy_to_clipboard(self):
        """
        Copies the current prompt text to the system clipboard.
        """
        clipboard = QApplication.clipboard()
        clipboard.setText(self.get_prompt_text())
        self.status_label.setText("Copied prompt to clipboard.")
        QTimer.singleShot(3000, lambda: self.status_label.setText(""))

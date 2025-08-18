# response_tab.py
# Persistent Assistant v3
# Created: 2025-08-18
# Author: G. Rapson
# Company: GR-Analysis
# Description:
#   Defines the ResponseTab class which will display the AI model's output.
#   For now, it uses a non-editable text viewer as a placeholder.

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit

class ResponseTab(QWidget):
    """
    A Qt tab that displays the AI-generated response.

    For now, this is a read-only text area to display mock or pasted responses.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        """
        Initializes the user interface layout for the ResponseTab.
        """
        layout = QVBoxLayout()

        self.label = QLabel("AI Response (read-only):")
        layout.addWidget(self.label)

        self.response_view = QTextEdit()
        self.response_view.setReadOnly(True)
        self.response_view.setPlaceholderText("Response from AI model will appear here...")
        layout.addWidget(self.response_view)

        self.setLayout(layout)

    def set_response_text(self, text: str):
        """
        Sets the content of the response view.

        Args:
            text (str): The AI response.
        """
        self.response_view.setPlainText(text)

    def get_response_text(self) -> str:
        """
        Returns the current displayed response.

        Returns:
            str: The AI response text.
        """
        return self.response_view.toPlainText()

# response_tab.py
# Persistent Assistant v3
# Created: 2025-08-18
# Author: G. Rapson
# Company: GR-Analysis
# Description:
#   Defines the ResponseTab class which will display the AI model's output.
#   For now, it uses a non-editable text viewer as a placeholder. Logs interactions automatically on paste.

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit
from PyQt6.QtWidgets import QPushButton, QFileDialog, QMessageBox
from PyQt6.QtGui import QClipboard
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
import os
import yaml
import datetime
from core.interaction_loader import load_interaction

class ResponseTab(QWidget):
    """
    A Qt tab that displays the AI-generated response.

    For now, this is a read-only text area to display mock or pasted responses.
    """
    def __init__(self, input_tab=None, prompt_tab=None, parent=None):
        super().__init__(parent)
        self.input_tab = input_tab
        self.prompt_tab = prompt_tab
        self.status_label = QLabel("")
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

        self.paste_button = QPushButton("Paste from Clipboard")
        self.paste_button.clicked.connect(self.paste_from_clipboard)
        layout.addWidget(self.paste_button)

        self.copy_button = QPushButton("Copy to Clipboard")
        self.copy_button.clicked.connect(self.copy_to_clipboard)
        layout.addWidget(self.copy_button)

        self.clear_button = QPushButton("Clear All")
        self.clear_button.clicked.connect(self.clear_all_texts)
        layout.addWidget(self.clear_button)

        self.log_button = QPushButton("Log Interaction")
        self.log_button.clicked.connect(
            lambda: self.log_interaction(
                self.input_tab.get_input_text(),
                self.prompt_tab.get_prompt_text()
            )
        )
        layout.addWidget(self.log_button)

        self.load_button = QPushButton("Load Interaction")
        self.load_button.clicked.connect(self.load_interaction_dialog)
        layout.addWidget(self.load_button)

        layout.addWidget(self.status_label)
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

    def paste_from_clipboard(self):
        """
        Pastes clipboard contents into the response view and logs it.
        """
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        self.set_response_text(text)
        self.log_interaction(
            self.input_tab.get_input_text(),
            self.prompt_tab.get_prompt_text()
        )

    def copy_to_clipboard(self):
        """
        Copies the response text to the system clipboard.
        """
        clipboard = QApplication.clipboard()
        clipboard.setText(self.get_response_text())
        self.status_label.setText("Copied response to clipboard.")
        QTimer.singleShot(3000, lambda: self.status_label.setText(""))

    def clear_all_texts(self):
        """
        Clears the input, prompt, and response views.
        """
        self.input_tab.text_edit.clear()
        self.prompt_tab.prompt_edit.clear()
        self.response_view.clear()
        self.status_label.setText("Cleared all fields.")
        QTimer.singleShot(3000, lambda: self.status_label.setText(""))

    def log_interaction(self, input_text: str, prompt_text: str):
        """
        Logs the interaction (input, prompt, response) to a YAML file with timestamp.

        Args:
            input_text (str): The original input text.
            prompt_text (str): The formatted prompt sent to ChatGPT.
        """
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"interaction_{timestamp}.yaml"
        log_dir = os.path.join("data", "interactions")
        os.makedirs(log_dir, exist_ok=True)
        filepath = os.path.join(log_dir, filename)

        data = {
            "development_stage": "10.7 of 15 to achieve MVP",
            "timestamp": timestamp,
            "source": "chatgpt-browser",
            "input_text": input_text,
            "prompt_text": prompt_text,
            "response_text": self.get_response_text()
        }

        with open(filepath, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True)

        self.status_label.setText(f"Interaction saved to {filepath}")
        QTimer.singleShot(6000, lambda: self.status_label.setText(""))

    def load_interaction_dialog(self):
        """
        Opens a file dialog to select a saved interaction and loads it.
        """
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Select interaction file",
            "data/interactions",
            "YAML Files (*.yaml);;All Files (*)"
        )

        if filepath:
            try:
                input_text, prompt_text, response_text = load_interaction(filepath)
                self.input_tab.text_edit.setPlainText(input_text)
                self.prompt_tab.set_prompt_text(prompt_text)
                self.set_response_text(response_text)
                self.status_label.setText(f"Loaded interaction: {os.path.basename(filepath)}")
            except Exception as e:
                QMessageBox.critical(self, "Load Error", str(e))

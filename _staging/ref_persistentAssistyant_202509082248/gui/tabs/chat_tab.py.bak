# chat_tab.py
# Persistent Assistant v3
# Created: 2025-08-18
# Author: G. Rapson
# Company: GR-Analysis
# Description:
#   Defines the ChatTab class which embeds ChatGPT in a QWebEngineView browser window.
#   This allows real-time interaction with OpenAI’s web interface until API integration.

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QUrl

class ChatTab(QWidget):
    """
    A Qt tab that embeds a browser window loading ChatGPT via QWebEngineView.

    This allows manual interaction with OpenAI’s web interface directly inside the GUI.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        """
        Initializes the layout and browser view for the embedded ChatGPT session.
        """
        layout = QVBoxLayout()

        self.label = QLabel("Embedded ChatGPT Browser:")
        layout.addWidget(self.label)

        self.browser = QWebEngineView()
        self.browser.page().profile().setHttpUserAgent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115 Safari/537.36")

        self.browser.load(QUrl("https://chat.openai.com"))
        layout.addWidget(self.browser)

        self.setLayout(layout)

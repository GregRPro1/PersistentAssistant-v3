from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton,
    QInputDialog, QMessageBox
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QUrl

class ChatTab(QWidget):
    """
    A Qt tab that embeds a browser window loading ChatGPT via QWebEngineView.

    Allows manual interaction with OpenAI’s web interface directly inside the GUI.
    Optional "Send to AI (API)" button wires through to core.ai_client.AIClient.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.label = QLabel("Embedded ChatGPT Browser:")
        layout.addWidget(self.label)

        self.browser = QWebEngineView()
        self.browser.page().profile().setHttpUserAgent(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/115 Safari/537.36"
        )
        self.browser.load(QUrl("https://chat.openai.com"))
        layout.addWidget(self.browser)
        self.setLayout(layout)

    def on_send_api_clicked(self):
        try:
            from core.ai_client import AIClient
        except Exception as e:
            QMessageBox.critical(self, "AI Error", f"AIClient import failed: {e}")
            return

        text, ok = QInputDialog.getMultiLineText(self, "Send to AI (API)", "Prompt:")
        if not ok or not (text or "").strip():
            return

        try:
            client = AIClient()
            reply = client.send(text)
            msg = reply if isinstance(reply, str) else str(reply)
            if len(msg) > 4000:
                msg = msg[:4000] + "\n... [truncated]"
            QMessageBox.information(self, "AI Reply", msg)
        except Exception as e:
            QMessageBox.critical(self, "AI Error", str(e))

    def ensure_api_send_button(self):
        try:
            layout = self.layout()
            if layout is None:
                layout = QVBoxLayout(self)
                self.setLayout(layout)
            if not hasattr(self, "api_send_btn"):
                self.api_send_btn = QPushButton("Send to AI (API)")
                self.api_send_btn.setObjectName("btn_send_api")
                self.api_send_btn.clicked.connect(self.on_send_api_clicked)
                layout.addWidget(self.api_send_btn)
        except Exception:
            pass

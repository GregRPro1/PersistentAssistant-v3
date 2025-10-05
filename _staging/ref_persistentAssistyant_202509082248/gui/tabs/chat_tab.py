# chat_tab.py (candidate for Step 6.1) — adds Role selector; uses tools.role_context
from __future__ import annotations
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QInputDialog, QMessageBox, QHBoxLayout, QComboBox
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QUrl

class ChatTab(QWidget):
    """
    Embedded ChatGPT browser + API send.
    Adds a Role selector (Architect / CodeGen / Reviewer) for API sends.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        hdr = QHBoxLayout()
        self.label = QLabel("Embedded ChatGPT Browser:")
        hdr.addWidget(self.label)

        self.role_combo = QComboBox()
        self.role_combo.addItems(["Architect","CodeGen","Reviewer"])
        self.role_combo.setObjectName("role_selector")
        hdr.addWidget(QLabel("Role:"))
        hdr.addWidget(self.role_combo)

        self.api_send_btn = QPushButton("Send to AI (API)")
        self.api_send_btn.setObjectName("btn_send_api")
        self.api_send_btn.clicked.connect(self.on_send_api_clicked)
        hdr.addWidget(self.api_send_btn)

        layout.addLayout(hdr)

        self.browser = QWebEngineView()
        self.browser.page().profile().setHttpUserAgent(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115 Safari/537.36")
        self.browser.load(QUrl("https://chat.openai.com"))
        layout.addWidget(self.browser)

    def ensure_api_send_button(self):
        # legacy compat: ensure button exists if upstream init differs
        try:
            if not hasattr(self, "api_send_btn"):
                self.api_send_btn = QPushButton("Send to AI (API)")
                self.api_send_btn.setObjectName("btn_send_api")
                self.api_send_btn.clicked.connect(self.on_send_api_clicked)
                self.layout().addWidget(self.api_send_btn)
        except Exception:
            pass

    def on_send_api_clicked(self):
        """Prompt text, apply Role system preface, send via AIClient."""
        try:
            from core.ai_client import AIClient
            from tools.role_context import get_role_system_text
        except Exception as e:
            QMessageBox.critical(self, "AI Error", f"Imports failed: {e}")
            return

        text, ok = QInputDialog.getMultiLineText(self, "Send to AI (API)", "Prompt:")
        if not ok or not (text or "").strip():
            return

        role = self.role_combo.currentText() if hasattr(self, "role_combo") else "Architect"
        system = get_role_system_text(role) or f"You are the {role}."
        full_prompt = f"[ROLE={role}]\n{system}\n\n{text}"

        try:
            client = AIClient()  # default openai model per your ai_client
            res = client.send(full_prompt)
            msg = res if isinstance(res, str) else str(res)
            if isinstance(res, dict) and "reply" in res:
                msg = res["reply"]
            if len(msg) > 4000: msg = msg[:4000] + "\n... [truncated]"
            QMessageBox.information(self, f"AI Reply ({role})", msg)
        except Exception as e:
            # first line of error for popup (summary) + full str for details
            first_line = str(e).splitlines()[0] if str(e) else "Unknown error"
            QMessageBox.critical(self, "AI Error", first_line)

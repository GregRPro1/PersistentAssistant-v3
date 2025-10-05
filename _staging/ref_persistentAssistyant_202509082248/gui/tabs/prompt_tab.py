# gui/tabs/prompt_tab.py — candidate with "Send (API + Memory)" button
from __future__ import annotations
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QPushButton, QMessageBox
from PyQt6.QtCore import Qt
from core.ai_client import AIClient

class PromptTab(QWidget):
    """
    Prompt editor with direct API send.
    Adds: 'Send (API + Memory)' -> AIClient.send(include_memory=True)
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        lay = QVBoxLayout(self)
        self.label = QLabel("Prompt")
        lay.addWidget(self.label)
        self.editor = QTextEdit()
        lay.addWidget(self.editor, 1)

        btn_row = QHBoxLayout()
        self.btn_copy = QPushButton("Copy to Clipboard")
        self.btn_send = QPushButton("Send (API + Memory)")
        btn_row.addWidget(self.btn_copy)
        btn_row.addWidget(self.btn_send)
        lay.addLayout(btn_row)

        self.btn_copy.clicked.connect(self.on_copy)
        self.btn_send.clicked.connect(self.on_send_api_memory)

    def on_copy(self):
        try:
            from PyQt6.QtGui import QGuiApplication
            cb = QGuiApplication.clipboard()
            cb.setText(self.editor.toPlainText())
            QMessageBox.information(self, "Copied", "Prompt copied to clipboard.")
        except Exception as e:
            QMessageBox.critical(self, "Copy Error", str(e))

    def on_send_api_memory(self):
        text = (self.editor.toPlainText() or "").strip()
        if not text:
            QMessageBox.warning(self, "Empty", "Enter a prompt first.")
            return
        try:
            import os, yaml
            provider = "openai"
            key = os.getenv("OPENAI_API_KEY")
            if not key and provider=="openai":
                with open("C:/Secure/api_keys/keys.yaml","r",encoding="utf-8") as f:
                    keys = yaml.safe_load(f) or {}
                key = (((keys.get("keys") or {}).get("default") or {}).get(provider) or {}).get("paid")
            if not key:
                QMessageBox.critical(self, "Key Error", "Missing API key for OpenAI.")
                return
            client = AIClient(provider=provider, key=key)
            res = client.send(text, include_memory=True)
            head = (res.get("reply") or "")[:4000]
            used = res.get("context_used")
            meta = f"\n\n[provider={res.get('provider')} model={res.get('model')} ctx={used} tokens={res.get('tokens_in')}/{res.get('tokens_out')} cost=${res.get('cost'):.6f}]"
            QMessageBox.information(self, "AI Reply", head + meta)
        except Exception as e:
            # show first line of stack for rapid triage
            import traceback
            tb1 = (traceback.format_exc().splitlines() or [""])[-1]
            QMessageBox.critical(self, "AI Error", f"{str(e)}\n{tb1}")

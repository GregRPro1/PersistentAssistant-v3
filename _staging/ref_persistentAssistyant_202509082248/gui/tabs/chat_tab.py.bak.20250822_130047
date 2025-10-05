# gui/tabs/chat_tab.py (v4.3 candidate) — auto-log token usage & cost to YAML/CSV
from __future__ import annotations
import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QHBoxLayout, QComboBox, QPushButton,
    QMessageBox, QInputDialog
)
from PyQt6.QtGui import QIcon, QPixmap, QColor, QPainter
from PyQt6.QtCore import QUrl
from PyQt6.QtWebEngineWidgets import QWebEngineView

def _dot(color: str, size: int = 10) -> QIcon:
    pix = QPixmap(size, size); pix.fill(QColor(0,0,0,0))
    p = QPainter(pix); p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    col = QColor(color); p.setBrush(col); p.setPen(col); r = size-1
    p.drawEllipse(0,0,r,r); p.end()
    return QIcon(pix)

def _status_to_icon(status: str) -> QIcon:
    s = (status or "").lower()
    if s == "success": return _dot("#2ecc71")
    if s == "error":   return _dot("#e74c3c")
    if s in ("disabled","skipped"): return _dot("#bdc3c7")
    return _dot("#f1c40f")

def _load_ai_models():
    try:
        from tools.model_loader import load_ai_models
        return load_ai_models()
    except Exception:
        return {"providers": {}}

def _load_probe_status():
    p = Path("data/insights/model_probe_status.yaml")
    if not p.exists(): return {}
    try:
        import yaml
        return yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}

def _find_cost(meta: dict):
    return meta.get("input_cost_per_1k"), meta.get("output_cost_per_1k")

class ChatTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._models = None
        self._status = None
        self.api_send_btn = None
        self.browser = None
        self.init_ui()

    def init_ui(self):
        from tools import session_store as sess

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Embedded Chat + Model Controls"))

        row = QHBoxLayout()
        self.provider_cb = QComboBox()
        self.model_cb    = QComboBox()
        self.mode_cb     = QComboBox(); self.mode_cb.addItems(["Browser","API"])
        row.addWidget(QLabel("Provider:")); row.addWidget(self.provider_cb, 1)
        row.addWidget(QLabel("Model:"));    row.addWidget(self.model_cb, 2)
        row.addWidget(QLabel("Mode:"));     row.addWidget(self.mode_cb)
        layout.addLayout(row)

        row2 = QHBoxLayout()
        self.price_lbl = QLabel("Price: –")
        self.ping_btn  = QPushButton("Ping Test")
        self.api_send_btn = QPushButton("Send to AI (API)")
        self.api_send_btn.setObjectName("btn_send_api")
        row2.addWidget(self.price_lbl, 1)
        row2.addWidget(self.ping_btn)
        row2.addWidget(self.api_send_btn)
        layout.addLayout(row2)

        layout.addWidget(QLabel("Embedded ChatGPT Browser:"))
        self.browser = QWebEngineView()
        self.browser.page().profile().setHttpUserAgent(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115 Safari/537.36"
        )
        self.browser.load(QUrl("https://chat.openai.com"))
        layout.addWidget(self.browser, 1)

        self._models = _load_ai_models()
        self._status = _load_probe_status()
        self._populate_providers()

        # restore last session
        last = sess.get(["chat_tab","selection"], {}) or {}
        if last:
            prov = (last.get("provider") or "").lower()
            modl = last.get("model") or ""
            mode = last.get("mode") or "Browser"
            i = self.provider_cb.findText(prov) if prov else -1
            if i >= 0: self.provider_cb.setCurrentIndex(i)
            self._populate_models()
            j = self.model_cb.findText(modl) if modl else -1
            if j >= 0: self.model_cb.setCurrentIndex(j); self._refresh_price()
            k = self.mode_cb.findText(mode) if mode else -1
            if k >= 0: self.mode_cb.setCurrentIndex(k)
        self._apply_mode()

        # signals
        self.provider_cb.currentIndexChanged.connect(self._on_provider_changed)
        self.model_cb.currentIndexChanged.connect(self._on_model_changed)
        self.mode_cb.currentIndexChanged.connect(self._on_mode_changed)
        self.ping_btn.clicked.connect(self._on_ping_model)
        self.api_send_btn.clicked.connect(self.on_send_api_clicked)

    def _providers(self):
        return list((self._models.get("providers") or {}).keys())

    def _populate_providers(self):
        self.provider_cb.clear()
        for prov in self._providers():
            self.provider_cb.addItem(prov)
        for i in range(self.provider_cb.count()):
            prov = self.provider_cb.itemText(i)
            if prov.lower() != "openai":
                self.provider_cb.model().item(i).setEnabled(False)
                self.provider_cb.model().item(i).setToolTip("Disabled in MVP")
        idx = self.provider_cb.findText("openai")
        self.provider_cb.setCurrentIndex(idx if idx >= 0 else 0)
        self._populate_models()

    def _populate_models(self):
        self.model_cb.clear()
        prov = (self.provider_cb.currentText() or "").lower()
        pdata = (self._models.get("providers") or {}).get(prov, {}) or {}
        models = (pdata.get("models") or {})
        for mid, meta in models.items():
            st = ((self._status.get("providers") or {}).get(prov, {}).get("models") or {}).get(mid, {})
            icon = _status_to_icon(st.get("status"))
            tip  = f"status: {st.get('status','unknown')}; err: {st.get('error')}"
            self.model_cb.addItem(icon, mid)
            self.model_cb.setItemData(self.model_cb.count()-1, tip)
            if prov != "openai":
                self.model_cb.model().item(self.model_cb.count()-1).setEnabled(False)
        if self.model_cb.count() > 0:
            self.model_cb.setCurrentIndex(0)
            self._refresh_price()

    def _refresh_price(self):
        prov = (self.provider_cb.currentText() or "").lower()
        mid  = self.model_cb.currentText() or ""
        meta = ((self._models.get("providers") or {}).get(prov, {}).get("models") or {}).get(mid, {}) or {}
        inp, out = _find_cost(meta)
        self.price_lbl.setText("Price: –" if (inp is None and out is None) else f"Price: in={inp} / out={out} ($/1K tokens)")

    def _persist(self):
        from tools import session_store as sess
        sess.set(["chat_tab","selection"], {
            "provider": (self.provider_cb.currentText() or "").lower(),
            "model": self.model_cb.currentText() or "",
            "mode": self.mode_cb.currentText() or "Browser"
        })

    def _apply_mode(self):
        mode = self.mode_cb.currentText() or "Browser"
        is_api = (mode == "API")
        if self.browser: self.browser.setVisible(not is_api)
        if self.api_send_btn: self.api_send_btn.setEnabled(is_api)

    def _on_provider_changed(self, *_): self._populate_models(); self._refresh_price(); self._persist()
    def _on_model_changed(self, *_):    self._refresh_price(); self._persist()
    def _on_mode_changed(self, *_):     self._apply_mode(); self._persist()

    def _on_ping_model(self):
        prov = (self.provider_cb.currentText() or "").lower()
        mid  = self.model_cb.currentText() or ""
        if prov != "openai":
            QMessageBox.information(self, "Ping", "Provider disabled in MVP."); return
        try:
            import subprocess, sys
            subprocess.run([sys.executable, "tools/model_ping.py"], check=False)
            QMessageBox.information(self, "Ping", f"Probe triggered for {prov}:{mid}. See insights.")
        except Exception as e:
            QMessageBox.critical(self, "Ping Error", str(e))

    def on_send_api_clicked(self):
        prov = (self.provider_cb.currentText() or "").lower()
        model = self.model_cb.currentText() or None
        if prov != "openai":
            QMessageBox.information(self, "API", "Only OpenAI is enabled in MVP."); return

        key = os.getenv("OPENAI_API_KEY")
        if not key:
            try:
                import yaml
                with open(r"C:\Secure\api_keys\keys.yaml","r",encoding="utf-8") as f:
                    ky = yaml.safe_load(f) or {}
                key = (((ky.get("keys") or {}).get("default") or {}).get("openai") or {}).get("paid")
            except Exception:
                key = None
        if not key:
            QMessageBox.critical(self, "AI Error", "No OpenAI API key found (set OPENAI_API_KEY or keys.yaml).")
            return

        from core.ai_client import AIClient
        from tools.interaction_logger import log_interaction
        text, ok = QInputDialog.getMultiLineText(self, "Send to AI (API)", "Prompt:")
        if not ok or not (text or "").strip(): return
        try:
            client = AIClient(provider="openai", key=key, model=model)
            res = client.send(text)
            # Log interaction (YAML + CSV)
            try:
                ypath = log_interaction(text, res, ui_source="ChatTab")
            except Exception as le:
                ypath = None
            # Show reply
            msg = res.get("reply","") if isinstance(res, dict) else str(res)
            if len(msg) > 4000: msg = msg[:4000] + "\n... [truncated]"
            if ypath:
                QMessageBox.information(self, "AI Reply", f"{msg}\n\n[Logged: {ypath}]")
            else:
                QMessageBox.information(self, "AI Reply", msg)
        except Exception as e:
            QMessageBox.critical(self, "AI Error", str(e))

    def ensure_api_send_button(self):
        if getattr(self, "api_send_btn", None) is None:
            self.api_send_btn = QPushButton("Send to AI (API)")
            self.api_send_btn.setObjectName("btn_send_api")
            self.api_send_btn.clicked.connect(self.on_send_api_clicked)
            try:
                self.layout().itemAt(1).layout().addWidget(self.api_send_btn)
            except Exception:
                self.layout().addWidget(self.api_send_btn)

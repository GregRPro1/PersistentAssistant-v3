# tmp/chat_tab_v41_candidate.py
# Persistent Assistant v3 — Phase 4.1 UI candidate
# - Provider dropdown: OpenAI enabled; others visible but disabled
# - Model dropdown: includes ChatGPT-5; traffic-light dot per probe status
# - Pricing label; Mode toggle (Browser/API); Ping Test button
from __future__ import annotations
import os, json, subprocess
from pathlib import Path

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QComboBox, QPushButton, QMessageBox
from PyQt6.QtGui import QIcon, QPixmap, QColor, QPainter
from PyQt6.QtCore import QUrl
from PyQt6.QtWebEngineWidgets import QWebEngineView

# --- Helpers (local; avoids importing half the app during review) ---

def _dot(color: str, size: int = 10) -> QIcon:
    pix = QPixmap(size, size)
    pix.fill(QColor(0,0,0,0))
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    qcol = QColor(color)
    p.setBrush(qcol)
    p.setPen(qcol)
    r = size-1
    p.drawEllipse(0,0,r,r)
    p.end()
    return QIcon(pix)

def _status_to_icon(status: str) -> QIcon:
    s = (status or "").lower()
    if s == "success":
        return _dot("#2ecc71")  # green
    if s == "error":
        return _dot("#e74c3c")  # red
    if s in ("disabled","skipped"):
        return _dot("#bdc3c7")  # grey
    return _dot("#f1c40f")      # amber/unknown

def _load_ai_models():
    # read from config/ai_models.yaml via tools/model_loader
    try:
        from tools.model_loader import load_ai_models
        return load_ai_models()
    except Exception:
        return {"providers": {}}

def _load_probe_status():
    p = Path("data/insights/model_probe_status.yaml")
    if not p.exists():
        return {}
    import yaml
    try:
        return yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}

def _find_cost(meta: dict) -> tuple[float|None,float|None]:
    return meta.get("input_cost_per_1k"), meta.get("output_cost_per_1k")

# --- Main ChatTab candidate ---

class ChatTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._browser = None
        self._build_ui()

    def _build_ui(self):
        v = QVBoxLayout(self)

        # Title
        v.addWidget(QLabel("Embedded Chat + Model Controls"))

        # Provider / Model / Mode row
        row = QHBoxLayout()
        self.provider_cb = QComboBox()
        self.model_cb    = QComboBox()
        self.mode_cb     = QComboBox()
        self.mode_cb.addItems(["Browser","API"])
        row.addWidget(QLabel("Provider:"))
        row.addWidget(self.provider_cb, 1)
        row.addWidget(QLabel("Model:"))
        row.addWidget(self.model_cb, 2)
        row.addWidget(QLabel("Mode:"))
        row.addWidget(self.mode_cb)
        v.addLayout(row)

        # Pricing + Actions
        row2 = QHBoxLayout()
        self.price_lbl = QLabel("Price: –")
        self.ping_btn  = QPushButton("Ping Test")
        self.api_btn   = QPushButton("Send to AI (API)")
        row2.addWidget(self.price_lbl, 1)
        row2.addWidget(self.ping_btn)
        row2.addWidget(self.api_btn)
        v.addLayout(row2)

        # Browser
        self.browser_lbl = QLabel("Embedded ChatGPT Browser:")
        v.addWidget(self.browser_lbl)
        self._browser = QWebEngineView()
        self._browser.page().profile().setHttpUserAgent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115 Safari/537.36")
        self._browser.load(QUrl("https://chat.openai.com"))
        v.addWidget(self._browser, 1)

        # Data
        self._models = _load_ai_models()
        self._status = _load_probe_status()
        self._populate_controls()

        # Signals
        self.provider_cb.currentIndexChanged.connect(self._on_provider_changed)
        self.model_cb.currentIndexChanged.connect(self._on_model_changed)
        self.mode_cb.currentIndexChanged.connect(self._on_mode_changed)
        self.ping_btn.clicked.connect(self._on_ping_model)
        self.api_btn.clicked.connect(self._on_send_api_clicked)

    def _providers(self):
        return list((self._models.get("providers") or {}).keys())

    def _populate_controls(self):
        # Providers: show all; only OpenAI enabled
        self.provider_cb.clear()
        providers = self._providers()
        for prov in providers:
            self.provider_cb.addItem(prov)
        # disable non-OpenAI providers (visible but disabled)
        for i in range(self.provider_cb.count()):
            prov = self.provider_cb.itemText(i)
            if prov.lower() != "openai":
                self.provider_cb.model().item(i).setEnabled(False)
                self.provider_cb.model().item(i).setToolTip("Future support; disabled in MVP")
        # default to OpenAI if present
        idx = providers.index("openai") if "openai" in providers else 0
        self.provider_cb.setCurrentIndex(idx if idx >= 0 else 0)
        self._populate_models()

    def _populate_models(self):
        self.model_cb.clear()
        prov = (self.provider_cb.currentText() or "").lower()
        pdata = (self._models.get("providers") or {}).get(prov, {}) or {}
        models = (pdata.get("models") or {})
        # Insert each model with traffic-light icon + tooltip
        for mid, meta in models.items():
            st = ((self._status.get("providers") or {}).get(prov, {}).get("models") or {}).get(mid, {})
            icon = _status_to_icon(st.get("status"))
            tip  = f"status: {st.get('status','unknown')}; err: {st.get('error')}"
            self.model_cb.addItem(icon, mid)
            self.model_cb.setItemData(self.model_cb.count()-1, tip)
            # disable non-OpenAI here too
            if prov != "openai":
                self.model_cb.model().item(self.model_cb.count()-1).setEnabled(False)
        # Select first item
        if self.model_cb.count() > 0:
            self.model_cb.setCurrentIndex(0)
            self._refresh_price()

    def _refresh_price(self):
        prov = (self.provider_cb.currentText() or "").lower()
        mid  = self.model_cb.currentText() or ""
        meta = ((self._models.get("providers") or {}).get(prov, {}).get("models") or {}).get(mid, {}) or {}
        inp, out = _find_cost(meta)
        if inp is None and out is None:
            self.price_lbl.setText("Price: –")
        else:
            self.price_lbl.setText(f"Price: in={inp} / out={out} ($ per 1K tokens)")

    def _on_provider_changed(self, *_):
        self._populate_models()

    def _on_model_changed(self, *_):
        self._refresh_price()

    def _on_mode_changed(self, *_):
        # No-op for now; Browser/API affects buttons/flows in later step
        pass

    def _on_ping_model(self):
        # Use the centralized runner to capture stdout/err in errors.log
        prov = (self.provider_cb.currentText() or "").lower()
        mid  = self.model_cb.currentText() or ""
        if prov != "openai":
            QMessageBox.information(self, "Ping", "Provider disabled in MVP.")
            return
        # Run: python tools/model_ping.py (will probe all, including selected)
        try:
            subprocess.run([os.path.join(os.path.dirname(os.sys.executable), "python.exe"),
                            "tools/model_ping.py"], check=False)
            QMessageBox.information(self, "Ping", f"Probe triggered for {prov}:{mid}. See insights for status.")
        except Exception as e:
            QMessageBox.critical(self, "Ping Error", str(e))

    def _on_send_api_clicked(self):
        # Keep minimal MVP flow; real wiring (Step 4.2)
        try:
            from core.ai_client import AIClient
        except Exception as e:
            QMessageBox.critical(self, "AI Error", f"AIClient import failed: {e}")
            return
        from PyQt6.QtWidgets import QInputDialog
        text, ok = QInputDialog.getMultiLineText(self, "Send to AI (API)", "Prompt:")
        if not ok or not (text or "").strip():
            return
        try:
            model = self.model_cb.currentText() or None
            client = AIClient(provider="openai", key=os.getenv("OPENAI_API_KEY"), model=model)
            res = client.send(text)
            msg = res.get("reply","") if isinstance(res, dict) else str(res)
            if len(msg) > 4000: msg = msg[:4000] + "\n... [truncated]"
            QMessageBox.information(self, "AI Reply", msg)
        except Exception as e:
            QMessageBox.critical(self, "AI Error", str(e))

# --- PA_ROOT_IMPORT ---
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# --- /PA_ROOT_IMPORT ---
import os, re, sys

PATH = r"gui\\tabs\\chat_tab.py"

def add_imports(s):
    need = [
        "from PyQt6.QtWidgets import QPushButton",
        "from PyQt6.QtWidgets import QInputDialog",
        "from PyQt6.QtWidgets import QMessageBox",
        "from PyQt6.QtWidgets import QVBoxLayout",
    ]
    out = s
    for imp in need:
        if imp not in out:
            # insert near other PyQt imports or at top
            m = re.search(r"from PyQt6\\.QtWidgets import .*$", out, flags=re.M)
            if m:
                pos = m.end()
                out = out[:pos] + "\\n" + imp + out[pos:]
            else:
                out = imp + "\\n" + out
    return out

def ensure_class_method(s, method_name, method_body):
    if method_name in s:
        return s, False
    # place inside class ChatTab
    m = re.search(r"(class\\s+ChatTab\\b.*?:)", s)
    if not m:
        # fallback: append to end (still valid but less ideal)
        return s + "\\n" + method_body + "\\n", True
    insert_pos = m.end()
    return s[:insert_pos] + "\\n" + method_body + "\\n" + s[insert_pos:], True

def ensure_init_calls(s):
    # ensure __init__ exists; if not, create a minimal one that calls ensure_api_send_button()
    m_class = re.search(r"class\\s+ChatTab\\b.*?:", s)
    if not m_class:
        return s, False
    class_start = m_class.end()
    # find existing __init__
    m_init = re.search(r"\\n\\s*def\\s+__init__\\s*\\(self[^)]*\\):", s[class_start:])
    if m_init:
        abs_pos = class_start + m_init.end()
        # inject call after def line
        injection = "\\n        try:\\n            self.ensure_api_send_button()\\n        except Exception:\\n            pass\\n"
        return s[:abs_pos] + injection + s[abs_pos:], True
    else:
        # create minimal __init__
        template = """
    def __init__(self, *args, **kwargs):
        try:
            super().__init__(*args, **kwargs)
        except Exception:
            try:
                super(ChatTab, self).__init__(*args, **kwargs)
            except Exception:
                pass
        try:
            self.ensure_api_send_button()
        except Exception:
            pass
"""
        # insert after class header
        return s[:class_start] + template + s[class_start:], True

def main():
    if not os.path.exists(PATH):
        print(f"[PATCH ERROR] Missing file: {PATH}"); return 2
    src = open(PATH,"r",encoding="utf-8",errors="ignore").read()

    # 1) imports
    src2 = add_imports(src)

    # 2) ensure ensure_api_send_button()
    method_body = """
    def ensure_api_send_button(self):
        \"""
        Ensure a Send to AI (API) button exists; create layout if missing; connect to handler.
        \"""
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
        except Exception as _e:
            pass
"""
    src3, added_method = ensure_class_method(src2, "def ensure_api_send_button(", method_body)

    # 3) ensure handler on_send_api_clicked()
    handler_body = """
    def on_send_api_clicked(self):
        \"""
        Prompt and send to AIClient.send(); show reply or error. Minimal Step 4.2 wiring.
        \"""
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
                msg = msg[:4000] + "\\n... [truncated]"
            QMessageBox.information(self, "AI Reply", msg)
        except Exception as e:
            QMessageBox.critical(self, "AI Error", str(e))
"""
    src4, added_handler = ensure_class_method(src3, "def on_send_api_clicked(", handler_body)

    # 4) ensure __init__ calls ensure_api_send_button()
    src5, touched_init = ensure_init_calls(src4)

    if src5 == src:
        print("[PATCH SKIP] No changes made.")
        return 0

    # backup and write
    bak = PATH + ".bak2"
    with open(bak,"w",encoding="utf-8") as f: f.write(src)
    with open(PATH,"w",encoding="utf-8") as f: f.write(src5)
    print("[PATCH OK] Constructor-based button + handler ensured; backup at", bak)
    return 0

if __name__ == "__main__":
    sys.exit(main())

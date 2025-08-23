# --- PA_ROOT_IMPORT ---
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# --- /PA_ROOT_IMPORT ---
import io, os, re, sys

PATH = r"gui\\tabs\\chat_tab.py"

def ensure_imports(src):
    lines = src.splitlines()
    need = {
        "QPushButton": "from PyQt6.QtWidgets import QPushButton",
        "QInputDialog": "from PyQt6.QtWidgets import QInputDialog",
        "QMessageBox": "from PyQt6.QtWidgets import QMessageBox",
        "QVBoxLayout": "from PyQt6.QtWidgets import QVBoxLayout",
    }
    present = set()
    for ln in lines:
        if "from PyQt6.QtWidgets import" in ln:
            for k in list(need):
                if k in ln:
                    present.add(k)
    missing = [need[k] for k in need if k not in present]
    if not missing:
        return src
    # inject missing imports right after the first PyQt6.QtWidgets import, else after first import
    for i, ln in enumerate(lines):
        if "from PyQt6.QtWidgets import" in ln:
            insert_at = i + 1
            break
    else:
        for i, ln in enumerate(lines):
            if ln.startswith("import ") or ln.startswith("from "):
                insert_at = i + 1
                break
        else:
            insert_at = 0
    new_lines = lines[:insert_at] + missing + lines[insert_at:]
    return "\n".join(new_lines)

def add_button_in_init_ui(src):
    if "Send to AI (API)" in src and "on_send_api_clicked" in src:
        return src, False  # already patched
    # locate init_ui
    m = re.search(r"\n\\s*def\\s+init_ui\\s*\\(self[^)]*\\):", src)
    if not m:
        # fallback: append at end of class by adding a minimal init_ui
        # but we prefer not to create whole init_ui; return unmodified
        return src, False
    # find end of init_ui by indentation heuristic
    start = m.end()
    # find indentation level of def line
    def_line = src[:m.end()].splitlines()[-1]
    indent = len(def_line) - len(def_line.lstrip())
    # insert just before the next method at same or lower indent, or end of file
    method_iter = list(re.finditer(r"\n\\s*def\\s+\\w+\\s*\\(", src[start:]))
    insert_pos = len(src)
    for mm in method_iter:
        # absolute pos
        abs_pos = start + mm.start()
        # compute indent of that def
        line = src[abs_pos:abs_pos+200].splitlines()[0]
        this_indent = len(line) - len(line.lstrip())
        if this_indent <= indent:
            insert_pos = abs_pos
            break

    injection = """
        try:
            layout = self.layout()
            if layout is None:
                layout = QVBoxLayout(self)
                self.setLayout(layout)
            self.api_send_btn = QPushButton("Send to AI (API)")
            self.api_send_btn.setObjectName("btn_send_api")
            self.api_send_btn.clicked.connect(self.on_send_api_clicked)
            layout.addWidget(self.api_send_btn)
        except Exception as _e:
            # non-fatal UI wiring issue; logged later if needed
            pass
"""
    patched = src[:insert_pos] + injection + src[insert_pos:]
    return patched, True

def append_handler(src):
    if "def on_send_api_clicked(" in src:
        return src, False
    handler = '''

    def on_send_api_clicked(self):
        """
        Open a prompt dialog and send text to AIClient.send(); show reply or error.
        Safe, minimal wiring for Step 4.2.
        """
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
            # show first chunk; avoid huge dialogs
            msg = reply if isinstance(reply, str) else str(reply)
            if len(msg) > 4000:
                msg = msg[:4000] + "\\n... [truncated]"
            QMessageBox.information(self, "AI Reply", msg)
        except Exception as e:
            QMessageBox.critical(self, "AI Error", str(e))
'''
    # append at end of class ChatTab if we can find it
    m = re.search(r"class\\s+ChatTab\\b.*?:", src)
    if not m:
        return src + handler, True
    # append to end of file (safe)
    return src + handler, True

def main():
    if not os.path.exists(PATH):
        print(f"[PATCH ERROR] Missing file: {PATH}")
        return 2
    original = open(PATH, "r", encoding="utf-8", errors="ignore").read()
    if "Send to AI (API)" in original and "on_send_api_clicked" in original:
        print("[PATCH SKIP] ChatTab already contains Send to AI (API) wiring.")
        return 0
    patched = ensure_imports(original)
    patched, changed1 = add_button_in_init_ui(patched)
    patched, changed2 = append_handler(patched)
    if not (changed1 or changed2):
        print("[PATCH WARN] Could not locate init_ui; no changes applied.")
        return 1
    # backup then write
    bak = PATH + ".bak"
    with open(bak, "w", encoding="utf-8") as f:
        f.write(original)
    with open(PATH, "w", encoding="utf-8") as f:
        f.write(patched)
    print("[PATCH OK] chat_tab.py updated; backup at", bak)
    return 0

if __name__ == "__main__":
    sys.exit(main())

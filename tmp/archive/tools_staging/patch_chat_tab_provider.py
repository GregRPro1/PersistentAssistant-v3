# --- PA_ROOT_IMPORT ---
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# --- /PA_ROOT_IMPORT ---
import os, re, sys

PATH = r"gui\\tabs\\chat_tab.py"

NEW_HANDLER = r"""
    def on_send_api_clicked(self):
        """
        Prompt and send to AIClient.send(); default OpenAI provider. Minimal Step 4.2 wiring.
        """
        try:
            from core.ai_client import AIClient
        except Exception as e:
            QMessageBox.critical(self, "AI Error", f"AIClient import failed: {e}")
            return

        # Prompt for message
        text, ok = QInputDialog.getMultiLineText(self, "Send to AI (API)", "Prompt:")
        if not ok or not (text or "").strip():
            return

        # Select provider/model (defaults for MVP)
        provider = "openai"
        model = "gpt-4o-mini"

        # Load API key (same convention as ai_client.py)
        key = None
        try:
            import yaml
            keys_path = r"C:\\Secure\api_keys\\keys.yaml"
            with open(keys_path, "r", encoding="utf-8") as f:
                keys = yaml.safe_load(f)
            key = ((keys or {}).get("keys") or {}).get("default", {}).get(provider, {}).get("paid")
        except Exception as e:
            QMessageBox.critical(self, "API Key Error", f"Failed to load API keys: {e}")
            return

        if not key:
            QMessageBox.critical(self, "API Key Error", "No API key found for provider 'openai' at C:\\Secure\\api_keys\\keys.yaml")
            return

        # Call provider
        try:
            client = AIClient(provider=provider, key=key, model=model)
            result = client.send(text)
            # Show brief reply; truncate for safety
            reply = result.get("reply", "")
            meta = f"\\n\\n[model={result.get('model')}] tokens_in={result.get('tokens_in')} tokens_out={result.get('tokens_out')} cost=${result.get('cost'):.6f}"
            if isinstance(reply, str) and len(reply) > 4000:
                reply = reply[:4000] + "\\n... [truncated]"
            QMessageBox.information(self, "AI Reply", (reply or "<no content>") + meta)
        except Exception as e:
            QMessageBox.critical(self, "AI Error", str(e))
"""

def main():
    if not os.path.exists(PATH):
        print(f"[PATCH ERROR] Missing file: {PATH}")
        return 2
    src = open(PATH, "r", encoding="utf-8", errors="ignore").read()

    # Replace existing handler (from def on_send_api_clicked to next def/class/end)
    m = re.search(r"\\n\\s*def\\s+on_send_api_clicked\\s*\\(self[^)]*\\):", src)
    if not m:
        print("[PATCH ERROR] on_send_api_clicked not found.")
        return 3
    start = m.start()

    # find end of method block by next def/class at same or lower indent, or end of file
    # Simple heuristic: cut until next "\n    def " or "\nclass " starting at same indentation level
    rest = src[m.end():]
    end_rel = len(rest)
    cut = re.search(r"\\n\\s*def\\s+\\w+\\s*\\(|\\nclass\\s+\\w+", rest)
    if cut:
        end_rel = cut.start()
    new_src = src[:start] + "\\n" + NEW_HANDLER + "\\n" + rest[end_rel:]

    # Backup then write
    bak = PATH + ".bak_provider"
    with open(bak, "w", encoding="utf-8") as f: f.write(src)
    with open(PATH, "w", encoding="utf-8") as f: f.write(new_src)
    print("[PATCH OK] on_send_api_clicked updated; backup at", bak)
    return 0

if __name__ == "__main__":
    sys.exit(main())

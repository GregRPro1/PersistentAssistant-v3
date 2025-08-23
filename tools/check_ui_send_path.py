# --- PA_ROOT_IMPORT ---
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# --- /PA_ROOT_IMPORT ---
import os, sys

AI_CLIENT = os.path.join("core","ai_client.py")
CHAT_TAB  = os.path.join("gui","tabs","chat_tab.py")

def scan(path):
    if not os.path.exists(path):
        return {"exists": False, "size": 0, "has_text": False}
    try:
        with open(path,"r",encoding="utf-8",errors="ignore") as f:
            s = f.read()
        return {"exists": True, "size": len(s), "has_text": "Send to AI (API)" in s,
                "has_handler": "def on_send_api_clicked" in s,
                "has_connect": ".clicked.connect(self.on_send_api_clicked)" in s}
    except Exception as e:
        return {"exists": True, "size": -1, "error": str(e)}

def main():
    a = scan(AI_CLIENT)
    c = scan(CHAT_TAB)
    print("== AI Client ==")
    print(f"path: {AI_CLIENT}")
    print(f"exists: {a.get('exists')}")

    print("\n== Chat Tab ==")
    print(f"path: {CHAT_TAB}")
    print(f"exists: {c.get('exists')}  size: {c.get('size')}")
    if "error" in c: print("error:", c["error"])
    print(f"has_text('Send to AI (API)'): {c.get('has_text')}")
    print(f"has_handler(on_send_api_clicked): {c.get('has_handler')}")
    print(f"has_connect(signal->handler): {c.get('has_connect')}")

    if a.get("exists") and c.get("exists") and c.get("has_text") and c.get("has_handler") and c.get("has_connect"):
        print("\n[VERDICT] UI is wired to AIClient.send (button + handler present).")
    else:
        missing=[]
        if not c.get("has_text"): missing.append("button text")
        if not c.get("has_handler"): missing.append("handler")
        if not c.get("has_connect"): missing.append("signal connect")
        print("\n[VERDICT] Wiring incomplete:", ", ".join(missing) or "(see details)")

if __name__ == "__main__":
    main()

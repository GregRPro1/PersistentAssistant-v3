#!/usr/bin/env python3
import os, sys, json, urllib.request

# Env vars required:
# WHATSAPP_TOKEN=EA.... ; WHATSAPP_PHONE_ID=your_whatsapp_business_phone_id ; WHATSAPP_TO=+44xxxx
TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_ID = os.getenv("WHATSAPP_PHONE_ID")
TO = os.getenv("WHATSAPP_TO")
if not (TOKEN and PHONE_ID and TO):
    print("[WA] Missing env vars: WHATSAPP_TOKEN, WHATSAPP_PHONE_ID, WHATSAPP_TO", file=sys.stderr)
    sys.exit(2)

def send_text(text: str) -> bool:
    url = f"https://graph.facebook.com/v20.0/{PHONE_ID}/messages"
    data = {
        "messaging_product": "whatsapp",
        "to": TO,
        "type": "text",
        "text": {"body": text}
    }
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    })
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            return 200 <= r.status < 300
    except Exception as e:
        print(f"[WA] send error: {e}", file=sys.stderr)
        return False

if __name__ == "__main__":
    msg = " ".join(sys.argv[1:]) or "Hello from PAL"
    ok = send_text(msg)
    print("OK" if ok else "FAIL")

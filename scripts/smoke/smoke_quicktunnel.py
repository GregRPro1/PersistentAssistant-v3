#!/usr/bin/env python3
import re, sys, os, glob, urllib.request, ssl, time
LOG_DIR = r"C:\_Repos\PersistentAssistant\logs\cloudflared"
def latest_log():
    files = sorted(glob.glob(os.path.join(LOG_DIR, "quick-tunnel_*.log")), key=os.path.getmtime, reverse=True)
    return files[0] if files else None
def extract_url(path):
    pat = re.compile(r"https://[A-Za-z0-9\-\.]+\.trycloudflare\.com")
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            m = pat.search(line)
            if m: return m.group(0)
    return None
def head(url):
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, method="HEAD")
    with urllib.request.urlopen(req, timeout=5, context=ctx) as r:
        return r.status
if __name__ == "__main__":
    log = latest_log()
    if not log:
        print("NOLOG"); sys.exit(2)
    url = extract_url(log)
    if not url:
        print("NOURL"); sys.exit(3)
    try:
        code = head(url)
        print(f"URL={url} STATUS={code}")
        sys.exit(0 if code == 200 else 4)
    except Exception as e:
        print(f"ERROR {e}")
        sys.exit(5)

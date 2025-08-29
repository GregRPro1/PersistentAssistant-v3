from __future__ import annotations
import os, json, ssl, urllib.request, pathlib, time, smtplib
from typing import Dict, Any

ROOT = pathlib.Path(__file__).resolve().parents[2]
WD   = ROOT / "tmp" / "watchdog"

def _log_local(note: str) -> None:
    WD.mkdir(parents=True, exist_ok=True)
    p = WD / "notify.log"
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(p, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {note}\n")

def send_notifications(cfg: Dict[str, Any], subject: str, body: str) -> None:
    _email(cfg, subject, body)
    _slack(cfg, f"{subject}: {body}")
    _whatsapp(cfg, subject, body)

def _email(cfg: Dict[str, Any], subject: str, body: str) -> None:
    e = cfg.get("notify", {}).get("email", {})
    if not (e.get("enabled") and e.get("smtp_host") and e.get("to")):
        return
    try:
        ctx = ssl.create_default_context()
        pw = os.getenv(str(e.get("password_env") or "")) or ""
        frm = e.get("from", "pa-watchdog@localhost")
        msg = f"Subject: {subject}\r\nFrom: {frm}\r\nTo: {e['to']}\r\n\r\n{body}"
        with smtplib.SMTP(e["smtp_host"], int(e.get("smtp_port", 587)), timeout=10) as s:
            s.starttls(context=ctx)
            if e.get("username") and pw:
                s.login(e["username"], pw)
            s.sendmail(frm, [e["to"]], msg)
    except Exception as ex:
        _log_local(f"email failed: {ex}")

def _slack(cfg: Dict[str, Any], text: str) -> None:
    sw = cfg.get("notify", {}).get("slack_webhook", {})
    if not (sw.get("enabled") and sw.get("url")):
        return
    try:
        data = json.dumps({"text": text}).encode("utf-8")
        req = urllib.request.Request(sw["url"], data=data, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=5).read()
    except Exception as ex:
        _log_local(f"slack failed: {ex}")

def _whatsapp(cfg: Dict[str, Any], subject: str, body: str) -> None:
    wa = cfg.get("notify", {}).get("whatsapp", {})
    if not wa.get("enabled"):
        return
    # placeholder: drop intent file
    try:
        out = WD / (f"whatsapp_{time.strftime('%Y%m%d_%H%M%S')}.json")
        with open(out, "w", encoding="utf-8") as f:
            json.dump({"to": wa.get("to", ""), "subject": subject, "body": body}, f)
    except Exception as ex:
        _log_local(f"whatsapp stub failed: {ex}")

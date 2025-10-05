from flask import Response
import os, json, time, uuid, glob

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def _approvals_dir():
    d = os.path.join(ROOT, "tmp", "phone", "approvals")
    os.makedirs(d, exist_ok=True)
    return d

def _j(o, code=200):
    return Response(json.dumps(o), mimetype="application/json", status=code)

def _recent():
    try:
        d = _approvals_dir()
        fs = sorted(glob.glob(os.path.join(d, "approve_*.json")), key=os.path.getmtime, reverse=True)[:25]
        items=[]
        for f in fs:
            try:
                items.append({"file": os.path.basename(f), "bytes": os.path.getsize(f)})
            except Exception:
                pass
        return _j({"ok": True, "approvals": items})
    except Exception as e:
        return _j({"ok": False, "err": str(e)}, 500)

def _next2():
    try:
        d = _approvals_dir()
        ts = int(time.time()); nonce = str(uuid.uuid4())
        p = os.path.join(d, f"approve_{ts}_{nonce}.json")
        with open(p, "w", encoding="utf-8") as f:
            f.write(json.dumps({"ok": True, "action": "NEXT", "ts": ts, "nonce": nonce}))
        sug = ["9.5a — Worker UX", "9.5b — Auto-process", "9.5c — Plan details"]
        return _j({"ok": True, "file": os.path.basename(p), "suggestions": sug})
    except Exception as e:
        return _j({"ok": False, "err": str(e)}, 500)

def register_extensions(app):
    try:
        have = {r.rule for r in app.url_map.iter_rules()}
    except Exception:
        have = set()
    if "/agent/recent" not in have:
        try: app.add_url_rule("/agent/recent", view_func=_recent, methods=["GET"])
        except Exception: pass
    if "/agent/next2" not in have:
        try: app.add_url_rule("/agent/next2", view_func=_next2, methods=["GET","POST"])
        except Exception: pass
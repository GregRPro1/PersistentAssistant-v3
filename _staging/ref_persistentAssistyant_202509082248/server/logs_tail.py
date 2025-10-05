# server/logs_tail.py
from flask import Blueprint, Response, request
import os, codecs, itertools, io

logs_bp = Blueprint("logs", __name__)

@logs_bp.route("/logs/tail", methods=["GET"])
def tail():
    n = int(request.args.get("n", 200))
    # try common log paths
    candidates = ["logs/app.log", "tmp/logs/app.log"]
    for p in candidates:
        if os.path.exists(p):
            with open(p, "rb") as f:
                # simple tail
                try:
                    f.seek(0, os.SEEK_END)
                    size = f.tell()
                    block = 4096
                    data = bytearray()
                    while size > 0 and len(data) < 200000:
                        size = max(0, size - block)
                        f.seek(size)
                        data[:0] = f.read(block)
                        if data.count(b"\n") >= n:
                            break
                    lines = data.splitlines()[-n:]
                    txt = b"\n".join(lines).decode("utf-8", "replace")
                except Exception:
                    f.seek(0)
                    txt = f.read().decode("utf-8","replace")[-20000:]
            return Response(txt, mimetype="text/plain")
    return Response("No logs found.", mimetype="text/plain")

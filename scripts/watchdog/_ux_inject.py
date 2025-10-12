
# _ux_inject.py — serve CSS and inject <link> into HTML responses
from __future__ import annotations
from flask import Blueprint, current_app, send_from_directory
from pathlib import Path

def install_ux(app):
    bp = Blueprint("pal_ux", __name__)
    here = Path(__file__).resolve()

    @bp.route("/_pal/ux.css")
    def css():
        return send_from_directory(str(here.parent), "_ux.css")

    @app.after_request
    def _inject_link(resp):
        try:
            ct = resp.headers.get("Content-Type","")
            if "text/html" in ct and b"<head" in resp.get_data():
                body = resp.get_data(as_text=True)
                if "/_pal/ux.css" not in body:
                    head_link = "<link rel='stylesheet' href='/_pal/ux.css'/>"
                    body = body.replace("<head>", "<head>" + head_link, 1)
                    resp.set_data(body)
        except Exception:
            pass
        return resp

    app.register_blueprint(bp)


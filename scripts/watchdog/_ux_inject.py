
# _ux_inject.py — PAL-UX B.2 inline CSS/JS injection
from __future__ import annotations
from flask import Blueprint, send_from_directory
from pathlib import Path

CSS_LINK = "<link rel='stylesheet' href='/_pal/ux.css'/>"
CSS_INLINE_TAG = "<!-- PAL-UX-INLINE B.2 -->"
JS_INLINE = """<script id='pal-ux-inline-js'>(function(){
  // Group consecutive .btn into a row for neat layout
  function groupBtns(){
    document.querySelectorAll('.pal-card').forEach(function(card){
      var btns = Array.from(card.querySelectorAll('.btn'));
      if (!btns.length) return;
      // Ensure their parent displays as flex if they share the same parent
      var parents = new Set(btns.map(function(b){return b.parentElement;}));
      parents.forEach(function(p){
        if (!p) return;
        var hasAny = p.querySelectorAll('.btn').length > 1;
        if (hasAny) { p.style.display='flex'; p.style.flexWrap='wrap'; p.style.gap='8px'; }
      });
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', groupBtns);
  else groupBtns();
})();</script>"""

def install_ux(app):
    bp = Blueprint("pal_ux", __name__)
    here = Path(__file__).resolve()

    @bp.route("/_pal/ux.css")
    def css():
        return send_from_directory(str(here.parent), "_ux.css")

    @app.after_request
    def _inject_assets(resp):
        try:
            ct = resp.headers.get("Content-Type","")
            if "text/html" in ct:
                body = resp.get_data(as_text=True)
                if "<head>" in body and "/_pal/ux.css" not in body:
                    body = body.replace("<head>", "<head>"+CSS_LINK, 1)
                if CSS_INLINE_TAG not in body:
                    inline = "<style>"+Path(here.parent/'_ux.css').read_text(encoding='utf-8')+"</style>"+CSS_INLINE_TAG+JS_INLINE
                    # Append before </body> or at end
                    if "</body>" in body:
                        body = body.replace("</body>", inline+"</body>", 1)
                    else:
                        body = body + inline
                resp.set_data(body)
        except Exception:
            pass
        return resp

    app.register_blueprint(bp)

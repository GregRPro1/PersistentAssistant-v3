import os, sys, importlib, traceback, json
    from pathlib import Path
    from typing import Dict, Any
    try:
        import yaml  # optional
    except Exception:
        yaml = None

    from flask import Flask, Response
    from werkzeug.middleware.dispatcher import DispatcherMiddleware
    from werkzeug.serving import run_simple

    DEFAULT_CANDIDATES = [
        ("server.apply_api",      "/apply"),
        ("server.proposal_api",   "/proposals"),
        ("server.serve_phone_clean","/phone"),
        ("server.phone_blueprint","/phone_bp"),
        ("server.settings_api",   "/settings"),
        ("server.logs_tail",      "/logs"),
        ("server.agent_sidecar",  "/sidecar"),
        ("server.agent_sidecar_wrapper","/sidecar_wrap"),
        ("server.micro_approvals","/approvals"),
        ("server.approvals_micro","/approvals_alt"),
        ("server.micro_leb_proxy","/leb"),
        ("serve_phone",           "/phone_legacy"),
        ("serve_phone_inline",    "/phone_inline"),
        ("tools.leb_server",      "/leb_tool"),
    ]

    def load_cfg(root: Path) -> Dict[str, Any]:
        cfg = {
            "host": "127.0.0.1",
            "port": 8765,
            "token_env": "PA_WEB_TOKEN",
            "candidates": [m for m,_ in DEFAULT_CANDIDATES]
        }
        f = root / "config" / "unified_server.yaml"
        if f.exists() and yaml:
            try:
                data = yaml.safe_load(f.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    cfg.update(data)
            except Exception as e:
                print(f"[unified] WARN: failed to parse {f}: {e}")
        return cfg

    def ensure_default_config(root: Path):
        f = root / "config" / "unified_server.yaml"
        if f.exists(): return
        f.parent.mkdir(parents=True, exist_ok=True)
        body = """# unified server configuration
host: 127.0.0.1
port: 8765
# name of env var that holds a Bearer token; if empty -> no token required on localhost
token_env: PA_WEB_TOKEN
# override import candidates (advanced)
candidates:
  - server.apply_api
  - server.proposal_api
  - server.serve_phone_clean
  - server.phone_blueprint
  - server.settings_api
  - server.logs_tail
  - server.agent_sidecar
  - server.agent_sidecar_wrapper
  - server.micro_approvals
  - server.approvals_micro
  - server.micro_leb_proxy
  - serve_phone
  - serve_phone_inline
  - tools.leb_server
"""
        f.write_text(body, encoding="utf-8")

    def find_repo_root(seed: Path) -> Path:
        p = seed
        for _ in range(10):
            if (p/".git").exists(): return p
            if p.parent == p: break
            p = p.parent
        return seed

    def as_wsgi(mod):
        """
        Accepts modules that expose one of:
          - app (Flask)
          - create_app() -> Flask
          - bp (Blueprint)
        Returns: (wsgi_app, how) or (None, reason)
        """
        app = getattr(mod, "app", None)
        if app is not None and hasattr(app, "wsgi_app"):
            return app.wsgi_app, "app"
        ca = getattr(mod, "create_app", None)
        if callable(ca):
            try:
                a = ca()
                if hasattr(a, "wsgi_app"): return a.wsgi_app, "create_app"
            except Exception as e:
                return None, f"create_app failed: {e}"
        bp = getattr(mod, "bp", None)
        if bp is not None:
            try:
                a = Flask(getattr(mod, "__name__", "bp_wrap"))
                a.register_blueprint(bp)
                return a.wsgi_app, "bp"
            except Exception as e:
                return None, f"bp wrap failed: {e}"
        return None, "no app/create_app/bp"

    def make_index_app(mounted: Dict[str, str]):
        app = Flask("unified_index")
        @app.get("/")
        def index():
            rows = "".join([f"<tr><td><code>{p}</code></td><td>{name}</td></tr>" for p,name in mounted.items()])
            html = f"""<!doctype html>
            <html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
            <title>PersistentAssistant — Unified Server</title>
            <style>
              body{{font-family:system-ui,Segoe UI,Roboto,Arial,sans-serif;margin:16px;max-width:900px}}
              table{{border-collapse:collapse;width:100%}}
              td,th{{border:1px solid #ddd;padding:6px}}
              code{{background:#f6f8fa;padding:2px 4px;border-radius:4px}}
              .ok{{color:#0a0}}
            </style></head><body>
              <h1>Unified Server</h1>
              <p class="ok">Running. <a href="/healthz">healthz</a></p>
              <h3>Mounted apps</h3>
              <table><tr><th>Path</th><th>Module</th></tr>{rows}</table>
              <p><a href="/status">Status</a> (if provided by a mounted module)</p>
            </body></html>"""
            return Response(html, mimetype="text/html")
        @app.get("/healthz")
        def healthz():
            return {"ok": True}
        return app

    def auth_middleware(app, token: str):
        if not token:
            return app  # no auth enforced
        def wrapper(environ, start_response):
            # allow localhost without token
            ra = environ.get("REMOTE_ADDR", "")
            if ra in ("127.0.0.1", "::1"):
                return app(environ, start_response)
            auth = environ.get("HTTP_AUTHORIZATION", "")
            if auth == f"Bearer {token}":
                return app(environ, start_response)
            start_response("401 Unauthorized", [("Content-Type","text/plain")])
            return [b"Unauthorized"]
        return wrapper

    def main():
        here = Path(__file__).resolve()
        root = find_repo_root(here)
        ensure_default_config(root)
        cfg = load_cfg(root)
        token = os.environ.get(cfg.get("token_env","") or "", "")

        # import and mount
        mounted_map = {}   # url_path -> modname
        wsgi_children = {} # url_path -> wsgi_app
        results = []
        for modname, default_path in DEFAULT_CANDIDATES:
            if modname not in cfg.get("candidates", []):
                continue
            try:
                mod = importlib.import_module(modname)
            except Exception as e:
                results.append({"module": modname, "status": "import_failed", "error": str(e)})
                continue
            wsgi, how = as_wsgi(mod)
            if wsgi:
                path = default_path
                # avoid collisions
                i = 2
                while path in wsgi_children:
                    path = f"{default_path}{i}"; i+=1
                wsgi_children[path] = wsgi
                mounted_map[path] = modname
                results.append({"module": modname, "status": "mounted", "path": path, "how": how})
            else:
                results.append({"module": modname, "status": "skipped", "reason": how})

        # root index app
        index_app = make_index_app(mounted_map)
        application = DispatcherMiddleware(index_app.wsgi_app, wsgi_children)
        application = auth_middleware(application, token)

        # write report
        outdir = root / "reports" / "ops"
        outdir.mkdir(parents=True, exist_ok=True)
        (outdir/"unified_server_report.json").write_text(json.dumps({
            "mounted": results,
            "host": cfg["host"],
            "port": cfg["port"],
            "token_env": cfg["token_env"],
        }, indent=2), encoding="utf-8")

        host = cfg.get("host","127.0.0.1")
        port = int(cfg.get("port", 8765))
        print(f"[unified] serving on http://{host}:{port}/  (mounted: {len(wsgi_children)})")
        run_simple(host, port, application, use_reloader=False)

    if __name__ == "__main__":
        main()
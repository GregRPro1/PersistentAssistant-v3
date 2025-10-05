# server/bootstrap_mounts.py
import importlib, os

def _import_app():
    app = None
    try:
        mod = importlib.import_module("pa_lan"); app = getattr(mod, "app", None)
    except Exception: pass
    if app is None:
        try:
            mod = importlib.import_module("server.pa_lan"); app = getattr(mod, "app", None)
        except Exception: pass
    if app is None:
        try:
            import pkgutil, server
            for _, name, _ in pkgutil.iter_modules(server.__path__):
                m = importlib.import_module(f"server.{name}")
                if hasattr(m, "app"):
                    app = getattr(m, "app"); break
        except Exception: pass
    if app is None:
        raise RuntimeError("Could not locate Flask 'app' (tried pa_lan and server.pa_lan).")
    return app

def _mount(app):
    try:
        wd_api = importlib.import_module("server.watchdog_api")
        if hasattr(wd_api, "bp"): (__import__('builtins').print('bootstrap: mount watchdog_api') if 'watchdog_api' not in getattr(app,'blueprints',{}) else __import__('builtins').print('bootstrap: watchdog_api already mounted'); app.register_blueprint(wd_api.bp) if 'watchdog_api' not in getattr(app,'blueprints',{}) else None)
    except Exception: pass
    try:
        wd_ui = importlib.import_module("server.watchdog_ui")
        if hasattr(wd_ui, "bp"): (__import__('builtins').print('bootstrap: mount watchdog_ui') if 'watchdog_ui' not in getattr(app,'blueprints',{}) else __import__('builtins').print('bootstrap: watchdog_ui already mounted'); app.register_blueprint(wd_ui.bp) if 'watchdog_ui' not in getattr(app,'blueprints',{}) else None)
    except Exception: pass

def main():
    app = _import_app()
    _mount(app)
    host = os.getenv("PA_HOST", "0.0.0.0")
    port = int(os.getenv("PA_PORT", "8776"))
    debug = os.getenv("PA_DEBUG", "0") == "1"
    app.run(host=host, port=port, debug=debug)

if __name__ == "__main__":
    main()


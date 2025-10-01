# server/bootstrap_mounts.py
# Boot runner that imports the existing app and mounts watchdog UI/API.
# Supports both 'pa_lan' and 'server.pa_lan' layouts.

import importlib
import os

def _import_app():
    app = None
    # Try top-level pa_lan first
    try:
        mod = importlib.import_module("pa_lan")
        app = getattr(mod, "app", None)
    except Exception:
        pass
    if app is None:
        try:
            mod = importlib.import_module("server.pa_lan")
            app = getattr(mod, "app", None)
        except Exception:
            pass
    if app is None:
        # Last resort: dynamic search for a module that exposes 'app' in server/
        try:
            import pkgutil, server
            for _, name, _ in pkgutil.iter_modules(server.__path__):
                m = importlib.import_module(f"server.{name}")
                if hasattr(m, "app"):
                    app = getattr(m, "app")
                    break
        except Exception:
            pass
    if app is None:
        raise RuntimeError("Could not locate Flask 'app' (tried pa_lan and server.pa_lan).")
    return app

def _mount(app):
    # Import and mount the blueprints if present
    try:
        wd_api = importlib.import_module("server.watchdog_api")
        if hasattr(wd_api, "bp"):
            app.register_blueprint(wd_api.bp)
    except Exception:
        pass
    try:
        wd_ui = importlib.import_module("server.watchdog_ui")
        if hasattr(wd_ui, "bp"):
            app.register_blueprint(wd_ui.bp)
    except Exception:
        pass

def main():
    app = _import_app()
    _mount(app)
    # Use environment overrides if present
    host = os.environ.get("PA_HOST", "0.0.0.0")
    port = int(os.environ.get("PA_PORT", "8776"))
    debug = os.environ.get("PA_DEBUG", "0") == "1"
    # Production-safe dev server; watchdog supervises anyway
    app.run(host=host, port=port, debug=debug)

if __name__ == "__main__":
    main()

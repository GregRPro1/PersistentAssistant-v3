# server/bootstrap_mounts.py
import importlib, os, sys, json, traceback
from datetime import datetime

LOG_PATH = os.path.join('tmp', 'logs', 'bootstrap_mounts.log')

def _log(msg, **kv):
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    rec = {"ts": datetime.utcnow().isoformat(timespec="seconds") + "Z", "msg": msg}
    rec.update(kv)
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass
    try:
        print(rec, file=sys.stderr, flush=True)
    except Exception:
        pass

def _import_app():
    app = None
    tried = []
    try:
        mod = importlib.import_module("pa_lan"); tried.append("pa_lan")
        app = getattr(mod, "app", None)
        if app: _log("found_app", source="pa_lan")
    except Exception as e:
        _log("import_error", module="pa_lan", error=str(e), tb=traceback.format_exc())
    if app is None:
        try:
            mod = importlib.import_module("server.pa_lan"); tried.append("server.pa_lan")
            app = getattr(mod, "app", None)
            if app: _log("found_app", source="server.pa_lan")
        except Exception as e:
            _log("import_error", module="server.pa_lan", error=str(e), tb=traceback.format_exc())
    if app is None:
        try:
            import pkgutil, server
            for _, name, _ in pkgutil.iter_modules(server.__path__):
                tried.append(f"server.{name}")
                m = importlib.import_module(f"server.{name}")
                if hasattr(m, "app"):
                    app = getattr(m, "app"); _log("found_app", source=f"server.{name}"); break
        except Exception as e:
            _log("import_error", module="server.*", error=str(e), tb=traceback.format_exc())
    if app is None:
        _log("fatal_no_app", tried=tried)
        raise RuntimeError("Could not locate Flask 'app' (tried: " + ", ".join(tried) + ")")
    return app

def _mount(app):
    try:
        wd_api = importlib.import_module("server.watchdog_api")
        if hasattr(wd_api, "bp"):
            app.register_blueprint(wd_api.bp); _log("mounted", blueprint="watchdog_api", prefix=getattr(wd_api.bp, "url_prefix", None))
        else:
            _log("missing_bp_attr", module="server.watchdog_api")
    except Exception as e:
        _log("mount_error", module="server.watchdog_api", error=str(e), tb=traceback.format_exc())
    try:
        wd_ui = importlib.import_module("server.watchdog_ui")
        if hasattr(wd_ui, "bp"):
            app.register_blueprint(wd_ui.bp); _log("mounted", blueprint="watchdog_ui", prefix=getattr(wd_ui.bp, "url_prefix", None))
        else:
            _log("missing_bp_attr", module="server.watchdog_ui")
    except Exception as e:
        _log("mount_error", module="server.watchdog_ui", error=str(e), tb=traceback.format_exc())
    try:
        @app.route("/__wd_diag")
        def __wd_diag():
            try:
                routes = [str(r) for r in app.url_map.iter_rules()]
            except Exception:
                routes = []
            return {
                "routes": routes,
                "has_api": any("/api/watchdog" in r for r in routes),
                "has_ui": any("/app/watchdog" in r for r in routes),
            }, 200
        _log("diag_ready", path="/__wd_diag")
    except Exception as e:
        _log("diag_endpoint_error", error=str(e), tb=traceback.format_exc())

def main():
    host = os.getenv("PA_HOST", "0.0.0.0")
    port = int(os.getenv("PA_PORT", "8776"))
    debug = os.getenv("PA_DEBUG", "0") == "1"
    app = _import_app()
    _mount(app)
    _log("run_app", host=host, port=port, debug=debug)
    app.run(host=host, port=port, debug=debug)

if __name__ == "__main__":
    main()

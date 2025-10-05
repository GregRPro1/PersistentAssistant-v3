# --- injected: write startup marker ---
import os
try:
    os.makedirs(os.path.join("tmp","logs"), exist_ok=True)
    with open(os.path.join("tmp","logs","server.startup.log"), "a", encoding="utf-8") as _f:
        _f.write("[BOOTSTRAP_ENTER_MARKER] pid=%s\n" % os.getpid())
except Exception:
    pass
# --- end injected ---
# server/bootstrap_mounts.py (minimal runner)
import importlib, os, logging, sys, traceback

def _log_setup():
    try:
        os.makedirs(os.path.join("tmp","logs"), exist_ok=True)
        logging.basicConfig(
            filename=os.path.join("tmp","logs","server.startup.log"),
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(message)s"
        )
    except Exception:
        pass

def _get_app():
    # Only import server.pa_lan.app — do NOT mount any extra blueprints here.
    mod = importlib.import_module("server.pa_lan")
    app = getattr(mod, "app", None)
    if app is None:
        raise RuntimeError("server.pa_lan.app not found")
    logging.info("Imported server.pa_lan.app")
    return app

def _ensure_probes(app):
    try:
        from flask import jsonify
        if not any(r.rule == "/healthz" for r in app.url_map.iter_rules()):
            @app.get("/healthz")
            def _healthz():
                return "OK", 200
        if not any(r.rule == "/__debug" for r in app.url_map.iter_rules()):
            @app.get("/__debug")
            def _dbg():
                routes = sorted({r.rule for r in app.url_map.iter_rules()})
                return "ROUTES:\n" + "\n".join(routes), 200
        logging.info("Probes ensured (/healthz, /__debug)")
    except Exception:
        logging.exception("Failed to ensure probes")

def main():
    _log_setup()
    try:
        app = _get_app()
        _ensure_probes(app)
        host = os.getenv("PA_HOST", "0.0.0.0")
        port = int(os.getenv("PA_PORT", "8776"))
        debug = os.getenv("PA_DEBUG", "0") == "1"
        logging.info("Starting Flask on %s:%s debug=%s", host, port, debug)
        app.run(host=host, port=port, debug=debug)
    except Exception:
        logging.exception("bootstrap_mounts failure")
        raise

if __name__ == "__main__":
    main()


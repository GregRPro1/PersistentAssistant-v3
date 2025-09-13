# server/app_registry.py
# Loaded by the wrapper (if present). Use this to register optional blueprints cleanly.

from importlib import import_module

def _attach_proposal_blueprint(app):
    """
    Try to import server.proposal_api and register its blueprint.
    Logs are printed but failures are non-fatal.
    """
    try:
        mod = import_module("server.proposal_api")
    except Exception as e:
        print("[app_registry] proposal_api import failed:", e)
        return False

    bp = getattr(mod, "bp", None) or getattr(mod, "proposal_bp", None)
    if bp is None and hasattr(mod, "create_blueprint"):
        try:
            bp = mod.create_blueprint()
        except Exception as e:
            print("[app_registry] create_blueprint() failed:", e)
            return False

    if bp is not None:
        try:
            app.register_blueprint(bp)
            print("[app_registry] registered /agent/propose from server.proposal_api")
            return True
        except Exception as e:
            print("[app_registry] register_blueprint failed:", e)
            return False

    print("[app_registry] proposal_api has no blueprint to register")
    return False

def register_extensions(app):
    """
    Entry-point called by the wrapper (best-effort).
    Add more attach_* calls here in the future as we grow.
    """
    ok1 = _attach_proposal_blueprint(app)
    print(f"[app_registry] summary: propose={'ok' if ok1 else 'skip'}")

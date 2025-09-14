# server/app_registry.py
from __future__ import annotations

def _have_rule(app, path: str) -> bool:
    """Return True if a route with exactly this path exists."""
    try:
        for r in app.url_map.iter_rules():
            if str(r) == path:
                return True
    except Exception:
        pass
    return False


def _try_register_bp(app, import_path: str, route_probe: str, label: str) -> None:
    """Import <import_path>.bp and register it unless route already present."""
    try:
        mod = __import__(import_path, fromlist=["bp"])
        bp = getattr(mod, "bp", None)
        if bp is None:
            print(f"[app_registry] {label}: no 'bp' attribute on {import_path}")
            return
        if _have_rule(app, route_probe):
            print(f"[app_registry] {label}: {route_probe} already present; skipping")
            return
        app.register_blueprint(bp)
        print(f"[app_registry] registered {route_probe} from {import_path}")
    except Exception as e:
        print(f"[app_registry] register {label} failed:", e)


def register_extensions(app) -> None:
    """Register optional blueprints (robust & idempotent)."""
    _try_register_bp(app, "server.proposal_api", "/agent/propose", "/agent/propose")
    _try_register_bp(app, "server.apply_api",    "/agent/apply",   "/agent/apply")

    print(
        "[app_registry] summary: propose={}; apply={}".format(
            "ok" if _have_rule(app, "/agent/propose") else "skip",
            "ok" if _have_rule(app, "/agent/apply") else "skip"
        )
    )


__all__ = ["register_extensions"]

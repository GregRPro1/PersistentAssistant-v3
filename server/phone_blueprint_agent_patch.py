import os
from server.phone_blueprint import register_phone_blueprint as _orig_register
try:
    from server.agent_bp import register_agent_bp as _reg_agent
except Exception:
    _reg_agent = None

def register_phone_blueprint(app):
    app = _orig_register(app)
    if _reg_agent:
        try:
            app = _reg_agent(app)
        except Exception:
            pass
    return app


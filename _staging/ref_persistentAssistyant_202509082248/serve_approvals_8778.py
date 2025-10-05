import os, sys, logging
from logging.handlers import RotatingFileHandler
from server.approvals_micro import build_app

ROOT = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(ROOT, "tmp", "logs", "approvals_8778.log")
os.makedirs(os.path.dirname(LOG), exist_ok=True)
handler = RotatingFileHandler(LOG, maxBytes=524288, backupCount=2)
logging.basicConfig(level=logging.INFO, handlers=[handler])

if __name__ == "__main__":
    app=build_app()
    app.run(host="0.0.0.0", port=8778, debug=False)

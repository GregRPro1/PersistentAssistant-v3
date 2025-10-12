
import logging, os
from logging.handlers import RotatingFileHandler
from pathlib import Path

def setup_logging():
    log_dir = Path('tmp/logs'); log_dir.mkdir(parents=True, exist_ok=True)
    fp = log_dir / 'pal.log'
    handler = RotatingFileHandler(fp, maxBytes=2_000_000, backupCount=3, encoding='utf-8')
    fmt = logging.Formatter('%(asctime)s %(levelname)s %(name)s %(message)s')
    handler.setFormatter(fmt)
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    if not any(isinstance(h, RotatingFileHandler) for h in root.handlers):
        root.addHandler(handler)

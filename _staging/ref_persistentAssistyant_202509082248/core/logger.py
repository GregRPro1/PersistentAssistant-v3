# core/logger.py
# Persistent Assistant v3
# Created: 2025-08-18
# Author: G. Rapson
# Company: GR-Analysis
# Description:
#   Central logging utility. Writes rotating logs to logs/app.log.

import logging
import os
from logging.handlers import RotatingFileHandler

_LOGGER = None

def get_logger(name: str = "app") -> logging.Logger:
    global _LOGGER
    if _LOGGER:
        return _LOGGER

    os.makedirs("logs", exist_ok=True)
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = False  # prevent duplicate console output

    # Rotating file handler ~5MB, 3 backups
    fh = RotatingFileHandler("logs/app.log", maxBytes=5_000_000, backupCount=3, encoding="utf-8")
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    _LOGGER = logger
    return logger

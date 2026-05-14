"""Structured logging for Mnemo. Outputs to stderr (stdout reserved for MCP protocol)."""

from __future__ import annotations

import logging
import os
import sys

_handler = logging.StreamHandler(sys.stderr)
_handler.setFormatter(logging.Formatter("[mnemo] %(levelname)s %(message)s"))

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(f"mnemo.{name}")
    if not logger.handlers:
        logger.addHandler(_handler)
        logger.propagate = False
    level = os.environ.get("MNEMO_LOG_LEVEL", "WARNING").upper()
    logger.setLevel(getattr(logging, level, logging.WARNING))
    return logger

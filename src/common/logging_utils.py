"""Shared logging utilities.

Usage:

  from common.logging_utils import get_logger
  logger = get_logger(__name__)
  logger.info("hello")

The first call configures logging for the whole process (console + rotating file
under `logs/authpulse.log`). Subsequent calls will not add duplicate handlers.
"""

from __future__ import annotations

import logging
import os
import sys
import threading
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Final


_CONFIG_LOCK: Final[threading.Lock] = threading.Lock()
_CONFIGURED: bool = False


def _project_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    # Fallback: .../src/common/logging_utils.py -> repo root is 2 levels up.
    return here.parents[2]


def _parse_level(level: str | None) -> int:
    if not level:
        return logging.INFO

    text = level.strip()
    if not text:
        return logging.INFO

    if text.isdigit():
        return int(text)

    return getattr(logging, text.upper(), logging.INFO)


def _configure_once() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    with _CONFIG_LOCK:
        if _CONFIGURED:
            return

        level = _parse_level(os.getenv("AUTHPULSE_LOG_LEVEL", "INFO"))
        root = logging.getLogger()
        root.setLevel(level)

        fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s - %(message)s")

        # Console handler (stdout)
        console = logging.StreamHandler(stream=sys.stdout)
        console.setLevel(level)
        console.setFormatter(fmt)

        # Rotating file handler
        logs_dir = _project_root() / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        logfile = logs_dir / "authpulse.log"

        file_handler = RotatingFileHandler(
            logfile,
            maxBytes=5 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
            delay=True,
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(fmt)

        # Avoid duplicates if something configured logging before us.
        existing = root.handlers

        has_console = any(
            isinstance(h, logging.StreamHandler)
            and not isinstance(h, logging.FileHandler)
            and getattr(h, "stream", None) is sys.stdout
            for h in existing
        )
        if not has_console:
            root.addHandler(console)

        logfile_str = str(logfile)
        has_same_rotating_file = any(
            isinstance(h, RotatingFileHandler)
            and getattr(h, "baseFilename", None) == logfile_str
            for h in existing
        )
        if not has_same_rotating_file:
            root.addHandler(file_handler)

        _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a logger configured for AuthPulse."""

    _configure_once()
    return logging.getLogger(name)

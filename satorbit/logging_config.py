"""Centralized logging configuration with file rotation."""

from __future__ import annotations

import logging
import logging.handlers
import sys
from pathlib import Path

from satorbit.config import get_settings

_configured = False


def setup_logging() -> logging.Logger:
    """Configure and return the application root logger."""
    global _configured
    if _configured:
        return logging.getLogger("satellite_tools")

    settings = get_settings()
    log_dir = Path(settings.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("satellite_tools")
    logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

    fmt = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    logger.addHandler(console)

    # Rotating file handler (10 MB, keep 5 backups)
    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / "satellite_tools.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    # Error-only file handler
    error_handler = logging.handlers.RotatingFileHandler(
        log_dir / "errors.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(fmt)
    logger.addHandler(error_handler)

    _configured = True
    logger.info("Logging initialized — level=%s, dir=%s", settings.log_level, log_dir)
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a child logger under the satellite_tools namespace."""
    setup_logging()
    return logging.getLogger(f"satellite_tools.{name}")

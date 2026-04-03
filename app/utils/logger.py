"""Centralised Loguru logger for AskVineet."""

import sys
from functools import lru_cache

from loguru import logger as _logger


def _configure_logger(level: str = "INFO", log_file: str | None = None) -> None:
    _logger.remove()  # Remove default handler

    # Console — human-readable
    _logger.add(
        sys.stderr,
        level=level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> — "
            "<level>{message}</level>"
        ),
        colorize=True,
    )

    # File — JSON structured
    if log_file:
        import pathlib

        pathlib.Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        _logger.add(
            log_file,
            level=level,
            rotation="10 MB",
            retention="1 week",
            serialize=True,  # JSON output
            enqueue=True,    # Thread-safe
        )


@lru_cache(maxsize=1)
def get_logger():
    """Return the configured Loguru logger (singleton)."""
    from app.config.settings import get_settings

    s = get_settings()
    _configure_logger(level=s.log_level, log_file=s.log_file)
    return _logger


# Convenience re-export so callers can do:  from app.utils.logger import logger
logger = get_logger()

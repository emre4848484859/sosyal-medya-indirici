"""Centralized and user-friendly logging setup."""

from __future__ import annotations

from pathlib import Path
import logging
import os
from logging.config import dictConfig

__all__ = ["setup_logging"]

LOG_DIR = Path("logs")
LOG_FILE_NAME = "bot.log"


class FriendlyFormatter(logging.Formatter):
    """Formatter that adds subtle hints and cleaner logger names."""

    LEVEL_HINTS = {
        logging.DEBUG: "Detailed trace message.",
        logging.INFO: "System is running smoothly.",
        logging.WARNING: "Attention recommended.",
        logging.ERROR: "Action required.",
        logging.CRITICAL: "Critical failure.",
    }

    LEVEL_ALIASES = {
        logging.DEBUG: "DEBUG",
        logging.INFO: "INFO ",
        logging.WARNING: "WARN ",
        logging.ERROR: "ERROR",
        logging.CRITICAL: "CRIT ",
    }

    def format(self, record: logging.LogRecord) -> str:  # noqa: D401
        record.level_label = self.LEVEL_ALIASES.get(record.levelno, record.levelname)
        hint = self.LEVEL_HINTS.get(record.levelno, "")
        record.hint_suffix = f" - {hint}" if hint else ""
        record.clean_name = record.name.split(".")[-1]
        return super().format(record)


def setup_logging(level: str | int | None = None, log_directory: str | Path = LOG_DIR) -> None:
    """Configure console + file logging with contextual, readable output."""

    effective_level = _normalize_level(level or os.getenv("LOG_LEVEL") or "INFO")
    log_dir = Path(log_directory)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / LOG_FILE_NAME

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "console": {
                    "()": "bot.logging.FriendlyFormatter",
                    "format": "%(asctime)s | %(level_label)s | %(clean_name)s:%(lineno)d | %(message)s%(hint_suffix)s",
                },
                "file": {
                    "format": "%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s",
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "console",
                    "level": effective_level,
                },
                "file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "filename": str(log_file),
                    "maxBytes": 5 * 1024 * 1024,
                    "backupCount": 2,
                    "encoding": "utf-8",
                    "formatter": "file",
                    "level": "DEBUG",
                },
            },
            "root": {
                "handlers": ["console", "file"],
                "level": effective_level,
            },
        }
    )


def _normalize_level(level: str | int) -> int:
    """Return a valid logging level for numeric or string inputs."""

    if isinstance(level, int):
        return level

    normalized = logging.getLevelName(str(level).upper())
    if isinstance(normalized, int):
        return normalized

    raise ValueError(f"Unsupported logging level: {level!r}")

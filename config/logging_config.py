"""Structured logging configuration."""

import logging
import logging.config
import sys

from config.settings import get_settings


def setup_logging() -> None:
    """Configure structured logging for the application."""
    settings = get_settings()
    level = logging.DEBUG if settings.debug else logging.INFO

    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
                "formatter": "standard",
                "level": level,
            },
        },
        "root": {
            "level": level,
            "handlers": ["console"],
        },
        "loggers": {
            "agents": {"level": level},
            "backend": {"level": level},
            "uvicorn": {"level": "INFO"},
            "httpx": {"level": "WARNING"},
        },
    }

    logging.config.dictConfig(config)

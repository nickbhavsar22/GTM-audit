"""FastAPI dependency injection."""

from config.settings import Settings, get_settings
from backend.models.base import get_db

__all__ = ["get_db", "get_settings"]

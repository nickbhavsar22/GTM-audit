"""Centralized application configuration via Pydantic BaseSettings."""

from functools import lru_cache
from pathlib import Path
from typing import Optional

_VERSION_FILE = Path(__file__).resolve().parent.parent / "VERSION"


def get_version() -> str:
    """Read the current app version from the VERSION file."""
    try:
        return _VERSION_FILE.read_text().strip()
    except FileNotFoundError:
        return "0.0.0"

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    app_name: str = "GTM Audit"
    debug: bool = False
    app_password: str = "changeme"

    # Database
    database_url: str = "sqlite:///./gtm_audit.db"

    # API Keys
    anthropic_api_key: str = ""
    semrush_api_key: Optional[str] = None
    crunchbase_api_key: Optional[str] = None
    g2_api_key: Optional[str] = None

    # LLM Config
    llm_model: str = "claude-sonnet-4-6-20250514"
    llm_max_tokens: int = 16000

    # Audit Config
    max_pages_full: int = 30
    max_pages_quick: int = 10
    audit_timeout_minutes: int = 45
    rate_limit_per_hour: int = 5

    # Screenshot / MCP Config
    screenshot_enabled: bool = True
    screenshot_max_pages: int = 8
    screenshot_viewport_width: int = 1440
    screenshot_viewport_height: int = 900
    mockup_generation_enabled: bool = True

    # Consultant / Branding
    consultant_name: str = "Bhavsar Growth Consulting"
    consultant_bio: str = (
        "Bhavsar Growth Consulting helps B2B SaaS companies build predictable "
        "pipeline through GTM strategy, positioning, and demand generation. "
        "With 20+ years of enterprise software marketing experience, we've "
        "helped companies from Series A to public build scalable go-to-market engines."
    )

    # Backend
    backend_host: str = "127.0.0.1"
    backend_port: int = 8000

    # Security
    cors_origins: str = "http://localhost:8501"
    expose_docs: bool = True

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache()
def get_settings() -> Settings:
    return Settings()

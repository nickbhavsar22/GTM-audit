"""Centralized application configuration via Pydantic BaseSettings."""

from functools import lru_cache
from typing import Optional

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
    llm_model: str = "claude-sonnet-4-5-20250929"
    llm_max_tokens: int = 8000

    # Audit Config
    max_pages_full: int = 30
    max_pages_quick: int = 10
    audit_timeout_minutes: int = 45
    rate_limit_per_hour: int = 5

    # Backend
    backend_host: str = "127.0.0.1"
    backend_port: int = 8000

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache()
def get_settings() -> Settings:
    return Settings()

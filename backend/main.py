"""FastAPI application factory and configuration."""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.models.base import init_db
from backend.routers import auth, audits, reports, websocket
from backend.middleware.rate_limit import RateLimitMiddleware
from config.logging_config import setup_logging
from config.settings import get_settings, get_version


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    setup_logging()
    init_db()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    docs_url = "/docs" if settings.expose_docs else None
    redoc_url = "/redoc" if settings.expose_docs else None
    openapi_url = "/openapi.json" if settings.expose_docs else None

    app = FastAPI(
        title="GTM Audit API",
        version=get_version(),
        lifespan=lifespan,
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
    )

    # CORS
    origins = [o.strip() for o in settings.cors_origins.split(",")]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Rate limiting
    app.add_middleware(RateLimitMiddleware)

    # Routers
    app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
    app.include_router(audits.router, prefix="/api/audits", tags=["audits"])
    app.include_router(reports.router, prefix="/api/reports", tags=["reports"])
    app.include_router(websocket.router, tags=["websocket"])

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app


app = create_app()

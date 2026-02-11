"""Session-based authentication middleware for API endpoints."""

from datetime import datetime

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware

from backend.models.base import SessionLocal
from backend.models.session import UserSession


# Paths that don't require authentication
PUBLIC_PATHS = {
    "/health",
    "/api/auth/login",
    "/api/reports/share",  # Share links are public
    "/docs",
    "/openapi.json",
    "/redoc",
}


class AuthMiddleware(BaseHTTPMiddleware):
    """Validates session tokens on protected endpoints."""

    async def dispatch(self, request: Request, call_next):
        # Skip auth for public paths and WebSocket
        path = request.url.path
        if any(path.startswith(p) for p in PUBLIC_PATHS):
            return await call_next(request)

        if request.scope.get("type") == "websocket":
            return await call_next(request)

        # Check for session token
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if not token:
            token = request.query_params.get("session_token", "")

        if not token:
            raise HTTPException(status_code=401, detail="Authentication required")

        # Validate session
        db = SessionLocal()
        try:
            session = (
                db.query(UserSession)
                .filter(
                    UserSession.session_token == token,
                    UserSession.is_active == True,
                )
                .first()
            )

            if not session:
                raise HTTPException(status_code=401, detail="Invalid session")

            if session.is_expired:
                session.is_active = False
                db.commit()
                raise HTTPException(status_code=401, detail="Session expired")

        finally:
            db.close()

        return await call_next(request)

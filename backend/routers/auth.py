"""Authentication endpoints."""

import secrets

import bcrypt
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.dependencies import get_db, get_settings
from backend.models.session import UserSession
from backend.schemas.auth import LoginRequest, LoginResponse
from config.settings import Settings

router = APIRouter()


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
) -> LoginResponse:
    """Validate password and create session."""
    stored = settings.app_password
    # Support bcrypt-hashed passwords (start with $2b$) and plaintext fallback
    matched = False
    if stored.startswith("$2b$"):
        matched = bcrypt.checkpw(request.password.encode(), stored.encode())
    else:
        matched = request.password == stored
    if matched:
        token = secrets.token_urlsafe(64)
        session = UserSession(session_token=token)
        db.add(session)
        db.commit()
        return LoginResponse(
            success=True,
            session_token=token,
            message="Login successful",
        )
    return LoginResponse(success=False, message="Invalid password")


@router.post("/logout")
async def logout(session_token: str, db: Session = Depends(get_db)) -> dict:
    """Invalidate a session."""
    session = (
        db.query(UserSession)
        .filter(UserSession.session_token == session_token)
        .first()
    )
    if session:
        session.is_active = False
        db.commit()
    return {"status": "logged_out"}

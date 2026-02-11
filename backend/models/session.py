"""UserSession ORM model — tracks authenticated sessions."""

import uuid
from datetime import datetime, timedelta

from sqlalchemy import Boolean, Column, DateTime, String

from backend.models.base import Base


class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_token = Column(String(128), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(
        DateTime, default=lambda: datetime.utcnow() + timedelta(hours=24)
    )
    is_active = Column(Boolean, default=True)
    ip_address = Column(String(45), nullable=True)

    @property
    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at

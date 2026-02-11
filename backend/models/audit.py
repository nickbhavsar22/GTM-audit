"""Audit ORM model — represents a single GTM audit run."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship

from backend.models.base import Base


class AuditStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AuditType(str, enum.Enum):
    QUICK = "quick"
    FULL = "full"


class Audit(Base):
    __tablename__ = "audits"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_url = Column(String(2048), nullable=False)
    company_name = Column(String(255), default="")
    audit_type = Column(SQLEnum(AuditType), default=AuditType.FULL)
    status = Column(SQLEnum(AuditStatus), default=AuditStatus.PENDING)

    # Scoring
    overall_score = Column(Float, nullable=True)
    overall_grade = Column(String(3), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Metadata
    error_message = Column(Text, nullable=True)
    pages_crawled = Column(Integer, default=0)
    screenshots_count = Column(Integer, default=0)

    # Relationships
    agent_results = relationship(
        "AgentResult", back_populates="audit", cascade="all, delete-orphan"
    )
    report = relationship(
        "Report", back_populates="audit", uselist=False, cascade="all, delete-orphan"
    )

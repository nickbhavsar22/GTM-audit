"""AgentResult ORM model — stores per-agent analysis results and progress."""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy import JSON as SAJSON
from sqlalchemy.orm import relationship

from backend.models.base import Base


class AgentResult(Base):
    __tablename__ = "agent_results"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    audit_id = Column(String(36), ForeignKey("audits.id"), nullable=False)
    agent_name = Column(String(100), nullable=False)
    status = Column(String(20), default="pending")

    # Results
    score = Column(Float, nullable=True)
    max_score = Column(Float, nullable=True)
    grade = Column(String(3), nullable=True)
    result_data = Column(SAJSON, nullable=True)
    analysis_text = Column(Text, nullable=True)
    recommendations = Column(SAJSON, nullable=True)

    # Progress
    progress_pct = Column(Integer, default=0)
    current_task = Column(String(255), nullable=True)

    # Timing
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Error tracking
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)

    # Relationship
    audit = relationship("Audit", back_populates="agent_results")

"""Report ORM model — stores generated HTML/Markdown reports."""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy import JSON as SAJSON
from sqlalchemy.orm import relationship

from backend.models.base import Base


class Report(Base):
    __tablename__ = "reports"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    audit_id = Column(String(36), ForeignKey("audits.id"), nullable=False, unique=True)

    # Content
    html_content = Column(Text, nullable=True)
    markdown_content = Column(Text, nullable=True)
    pdf_path = Column(String(512), nullable=True)

    # Metadata
    report_metadata = Column(SAJSON, nullable=True)
    share_token = Column(String(64), nullable=True, unique=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    # Relationship
    audit = relationship("Audit", back_populates="report")

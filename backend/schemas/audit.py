"""Pydantic schemas for audit requests and responses."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, HttpUrl


class AuditCreateRequest(BaseModel):
    company_url: str
    audit_type: str = "full"  # "full" or "quick"


class AgentStatusResponse(BaseModel):
    agent_name: str
    status: str
    progress_pct: int = 0
    current_task: str = ""
    score: Optional[float] = None
    grade: Optional[str] = None
    error_message: Optional[str] = None

    model_config = {"from_attributes": True}


class AuditStatusResponse(BaseModel):
    id: str
    company_url: str
    company_name: str = ""
    audit_type: str
    status: str
    overall_score: Optional[float] = None
    overall_grade: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    agents: list[AgentStatusResponse] = []

    model_config = {"from_attributes": True}


class AuditResponse(BaseModel):
    id: str
    company_url: str
    company_name: str = ""
    audit_type: str
    status: str
    overall_score: Optional[float] = None
    overall_grade: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    pages_crawled: int = 0
    screenshots_count: int = 0
    error_message: Optional[str] = None

    model_config = {"from_attributes": True}

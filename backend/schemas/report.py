"""Pydantic schemas for report responses."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ReportResponse(BaseModel):
    id: str
    audit_id: str
    html_content: Optional[str] = None
    markdown_content: Optional[str] = None
    pdf_path: Optional[str] = None
    share_token: Optional[str] = None
    report_metadata: Optional[dict] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ExportRequest(BaseModel):
    format: str = "pdf"  # "pdf", "markdown", "html"

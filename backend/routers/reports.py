"""Report retrieval and export endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from backend.dependencies import get_db
from backend.schemas.report import ReportResponse
from backend.services.report_service import ReportService

router = APIRouter()


@router.get("/{audit_id}/report", response_model=ReportResponse)
async def get_report(audit_id: str, db: Session = Depends(get_db)) -> ReportResponse:
    """Retrieve the report for an audit."""
    service = ReportService(db)
    report = service.get_report(audit_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return ReportResponse.model_validate(report)


@router.get("/share/{share_token}", response_class=HTMLResponse)
async def get_shared_report(share_token: str, db: Session = Depends(get_db)):
    """View a shared report by token (no auth required)."""
    service = ReportService(db)
    report = service.get_report_by_token(share_token)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return HTMLResponse(content=report.html_content or "<h1>No report content</h1>")

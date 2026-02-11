"""Audit CRUD endpoints."""

import asyncio

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.dependencies import get_db
from backend.schemas.audit import (
    AuditCreateRequest,
    AuditResponse,
    AuditStatusResponse,
)
from backend.services.audit_service import AuditService

router = APIRouter()


@router.post("/create", response_model=AuditResponse)
async def create_audit(
    request: AuditCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> AuditResponse:
    """Create and start a new audit."""
    service = AuditService(db)
    audit = service.create_audit(request.company_url, request.audit_type)
    background_tasks.add_task(service.run_audit_async, audit.id)
    return AuditResponse.model_validate(audit)


@router.get("/{audit_id}/status", response_model=AuditStatusResponse)
async def get_audit_status(
    audit_id: str, db: Session = Depends(get_db)
) -> AuditStatusResponse:
    """Get real-time status of all agents for an audit."""
    service = AuditService(db)
    try:
        return service.get_status(audit_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Audit not found")


@router.get("/history", response_model=list[AuditResponse])
async def get_audit_history(db: Session = Depends(get_db)) -> list[AuditResponse]:
    """List all past audits."""
    service = AuditService(db)
    audits = service.list_audits()
    return [AuditResponse.model_validate(a) for a in audits]


@router.delete("/{audit_id}")
async def delete_audit(audit_id: str, db: Session = Depends(get_db)) -> dict:
    """Delete an audit and its results."""
    service = AuditService(db)
    if service.delete_audit(audit_id):
        return {"status": "deleted"}
    raise HTTPException(status_code=404, detail="Audit not found")

"""Core business logic for audit operations."""

import asyncio
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from backend.models.audit import Audit, AuditStatus, AuditType
from backend.models.agent_result import AgentResult
from backend.models.base import SessionLocal
from backend.schemas.audit import AgentStatusResponse, AuditStatusResponse
from config.constants import ALL_AGENT_NAMES, QUICK_AUDIT_AGENTS

logger = logging.getLogger(__name__)


class AuditService:
    def __init__(self, db: Session):
        self.db = db

    def create_audit(self, company_url: str, audit_type: str) -> Audit:
        """Create an audit record and pre-create agent_result rows."""
        audit = Audit(
            company_url=company_url,
            audit_type=AuditType(audit_type),
        )
        self.db.add(audit)
        self.db.flush()

        # Determine which agents to use based on audit type
        agent_names = (
            QUICK_AUDIT_AGENTS if audit_type == "quick" else ALL_AGENT_NAMES
        )
        for name in agent_names:
            self.db.add(AgentResult(audit_id=audit.id, agent_name=name))

        self.db.commit()
        self.db.refresh(audit)
        return audit

    def get_audit(self, audit_id: str) -> Optional[Audit]:
        return self.db.query(Audit).filter(Audit.id == audit_id).first()

    def get_status(self, audit_id: str) -> AuditStatusResponse:
        """Get audit status with all agent progress details."""
        audit = self.get_audit(audit_id)
        if not audit:
            raise ValueError(f"Audit {audit_id} not found")

        agents = [
            AgentStatusResponse(
                agent_name=r.agent_name,
                status=r.status,
                progress_pct=r.progress_pct or 0,
                current_task=r.current_task or "",
                score=r.score,
                grade=r.grade,
                error_message=r.error_message,
            )
            for r in audit.agent_results
        ]

        return AuditStatusResponse(
            id=audit.id,
            company_url=audit.company_url,
            company_name=audit.company_name or "",
            audit_type=audit.audit_type.value if audit.audit_type else "full",
            status=audit.status.value if audit.status else "pending",
            overall_score=audit.overall_score,
            overall_grade=audit.overall_grade,
            error_message=audit.error_message,
            created_at=audit.created_at,
            started_at=audit.started_at,
            completed_at=audit.completed_at,
            agents=agents,
        )

    def list_audits(self, limit: int = 50) -> list[Audit]:
        return (
            self.db.query(Audit)
            .order_by(Audit.created_at.desc())
            .limit(limit)
            .all()
        )

    def delete_audit(self, audit_id: str) -> bool:
        audit = self.get_audit(audit_id)
        if audit:
            self.db.delete(audit)
            self.db.commit()
            return True
        return False

    async def run_audit_async(self, audit_id: str) -> None:
        """Background task: run the full audit pipeline."""
        db = SessionLocal()
        try:
            audit = db.query(Audit).filter(Audit.id == audit_id).first()
            if not audit:
                logger.error(f"Audit {audit_id} not found")
                return

            audit.status = AuditStatus.RUNNING
            audit.started_at = datetime.utcnow()
            db.commit()

            # Import here to avoid circular imports
            from agents.context_store import ContextStore
            from agents.llm_client import LLMClient
            from agents.message_bus import MessageBus
            from agents.orchestrator import ProjectLead

            context = ContextStore(
                company_url=audit.company_url,
                audit_id=audit.id,
                audit_type=audit.audit_type.value if audit.audit_type else "full",
            )
            bus = MessageBus()
            llm = LLMClient()

            orchestrator = ProjectLead(
                context=context,
                message_bus=bus,
                llm_client=llm,
                db_session=db,
            )
            await orchestrator.run_audit()

            # Verify report was actually saved before marking complete
            from backend.models.report import Report

            report_exists = (
                db.query(Report).filter(Report.audit_id == audit_id).first()
            )

            if report_exists:
                audit.status = AuditStatus.COMPLETED
                audit.completed_at = datetime.utcnow()
                audit.pages_crawled = len(context.pages)
                audit.screenshots_count = len(context.screenshots)
            else:
                audit.status = AuditStatus.FAILED
                audit.error_message = (
                    "Audit agents completed but report was not saved to database"
                )
            db.commit()

            logger.info(f"Audit {audit_id} completed successfully")

        except Exception as e:
            logger.exception(f"Audit {audit_id} failed: {e}")
            audit = db.query(Audit).filter(Audit.id == audit_id).first()
            if audit:
                audit.status = AuditStatus.FAILED
                audit.error_message = str(e)
                db.commit()
        finally:
            db.close()

"""Report storage, retrieval, and export service."""

import logging
from typing import Optional

from sqlalchemy.orm import Session

from backend.models.report import Report

logger = logging.getLogger(__name__)


class ReportService:
    def __init__(self, db: Session):
        self.db = db

    def get_report(self, audit_id: str) -> Optional[Report]:
        return (
            self.db.query(Report)
            .filter(Report.audit_id == audit_id)
            .first()
        )

    def get_report_by_token(self, share_token: str) -> Optional[Report]:
        return (
            self.db.query(Report)
            .filter(Report.share_token == share_token)
            .first()
        )

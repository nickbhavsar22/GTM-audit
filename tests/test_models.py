"""Tests for SQLAlchemy ORM models."""

from backend.models.audit import Audit, AuditStatus, AuditType
from backend.models.agent_result import AgentResult
from backend.models.report import Report
from backend.models.session import UserSession


class TestAuditModel:
    def test_create_audit(self, db_session):
        audit = Audit(company_url="https://example.com", audit_type=AuditType.FULL)
        db_session.add(audit)
        db_session.commit()

        assert audit.id is not None
        assert audit.company_url == "https://example.com"
        assert audit.audit_type == AuditType.FULL
        assert audit.status == AuditStatus.PENDING
        assert audit.created_at is not None

    def test_audit_default_status(self, db_session):
        audit = Audit(company_url="https://test.com")
        db_session.add(audit)
        db_session.commit()

        assert audit.status == AuditStatus.PENDING

    def test_audit_relationships(self, db_session):
        audit = Audit(company_url="https://example.com")
        db_session.add(audit)
        db_session.commit()

        # Add agent result
        result = AgentResult(audit_id=audit.id, agent_name="seo")
        db_session.add(result)
        db_session.commit()

        assert len(audit.agent_results) == 1
        assert audit.agent_results[0].agent_name == "seo"

    def test_delete_cascade(self, db_session):
        audit = Audit(company_url="https://example.com")
        db_session.add(audit)
        db_session.commit()

        result = AgentResult(audit_id=audit.id, agent_name="seo")
        report = Report(audit_id=audit.id)
        db_session.add_all([result, report])
        db_session.commit()

        db_session.delete(audit)
        db_session.commit()

        assert db_session.query(AgentResult).count() == 0
        assert db_session.query(Report).count() == 0


class TestAgentResultModel:
    def test_create_agent_result(self, db_session):
        audit = Audit(company_url="https://example.com")
        db_session.add(audit)
        db_session.commit()

        result = AgentResult(
            audit_id=audit.id,
            agent_name="seo",
            status="running",
            progress_pct=50,
            current_task="Analyzing meta tags",
        )
        db_session.add(result)
        db_session.commit()

        assert result.id is not None
        assert result.progress_pct == 50
        assert result.current_task == "Analyzing meta tags"

    def test_agent_result_json_fields(self, db_session):
        audit = Audit(company_url="https://example.com")
        db_session.add(audit)
        db_session.commit()

        result = AgentResult(
            audit_id=audit.id,
            agent_name="seo",
            result_data={"keywords": ["test", "seo"]},
            recommendations=[{"issue": "Missing meta", "fix": "Add meta tags"}],
        )
        db_session.add(result)
        db_session.commit()

        fetched = db_session.query(AgentResult).filter_by(id=result.id).first()
        assert fetched.result_data["keywords"] == ["test", "seo"]
        assert len(fetched.recommendations) == 1


class TestReportModel:
    def test_create_report(self, db_session):
        audit = Audit(company_url="https://example.com")
        db_session.add(audit)
        db_session.commit()

        report = Report(
            audit_id=audit.id,
            html_content="<h1>Report</h1>",
            markdown_content="# Report",
        )
        db_session.add(report)
        db_session.commit()

        assert report.id is not None
        assert audit.report is not None
        assert audit.report.html_content == "<h1>Report</h1>"


class TestUserSessionModel:
    def test_create_session(self, db_session):
        session = UserSession(session_token="test-token-123")
        db_session.add(session)
        db_session.commit()

        assert session.id is not None
        assert session.is_active is True
        assert session.is_expired is False

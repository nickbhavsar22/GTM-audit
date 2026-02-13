"""Jinja2 HTML report rendering engine."""

import base64
import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from reports.scoring import AuditReport

logger = logging.getLogger(__name__)


class ReportRenderer:
    """Renders audit results into HTML using Jinja2 templates."""

    def __init__(self, template_dir: Path | None = None):
        self.template_dir = template_dir or Path(__file__).parent / "templates"
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=True,
        )
        # Register custom filters
        self.env.filters["score_color"] = self._score_color
        self.env.filters["grade_color"] = self._grade_color

    def render_html(self, report: AuditReport, company_profile: dict | None = None) -> str:
        """Render full HTML report."""
        template_name = (
            "quick_report.html"
            if report.audit_type == "quick"
            else "full_report.html"
        )
        template = self.env.get_template(template_name)

        # Load logo as base64 for embedding in standalone HTML reports
        logo_path = Path(__file__).parent.parent / "frontend" / "assets" / "images" / "bgc_logo.png"
        logo_base64 = ""
        if logo_path.exists():
            logo_base64 = base64.b64encode(logo_path.read_bytes()).decode()

        return template.render(
            report=report,
            company_name=report.company_name,
            company_url=report.company_url,
            overall_score=report.overall_percentage,
            overall_grade=report.overall_grade.value,
            modules=report.modules,
            recommendations=report.get_all_recommendations()[:20],
            quick_wins=report.get_quick_wins(5),
            strengths=report.get_top_strengths(5),
            critical_gaps=report.get_critical_gaps(5),
            company_profile=company_profile or {},
            logo_base64=logo_base64,
        )

    @staticmethod
    def _score_color(score: float) -> str:
        if score >= 80:
            return "#22C55E"  # green
        elif score >= 60:
            return "#EAB308"  # yellow
        elif score >= 40:
            return "#F97316"  # orange
        return "#EF4444"  # red

    @staticmethod
    def _grade_color(grade: str) -> str:
        if grade.startswith("A"):
            return "#22C55E"
        elif grade.startswith("B"):
            return "#3B82F6"
        elif grade.startswith("C"):
            return "#EAB308"
        return "#EF4444"

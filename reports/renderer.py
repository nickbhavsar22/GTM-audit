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

    def _load_embedded_fonts(self) -> str:
        """No longer embedding fonts — using system fallback stack per brand guidelines."""
        return ""

    def render_html(
        self,
        report: AuditReport,
        company_profile: dict | None = None,
        screenshots: dict | None = None,
        screenshot_diagnostic: str = "",
        executive_narrative: str = "",
        annotated_screenshots: list[dict] | None = None,
    ) -> str:
        """Render full HTML report with optional screenshot embedding."""
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

        # Load embedded fonts for self-contained rendering
        embedded_font_css = self._load_embedded_fonts()

        # Build screenshot data for template
        screenshot_data = {}
        module_screenshots = {}
        mockup_pairs = []

        if screenshots:
            screenshot_data, module_screenshots, mockup_pairs = self._process_screenshots(
                screenshots, report
            )

        from config.settings import get_version

        # For quick reports, keep content concise
        is_quick = report.audit_type == "quick"
        max_recs = 10 if is_quick else 20
        max_highlights = 3 if is_quick else 5

        # Load consultant settings
        from config.settings import get_settings
        settings = get_settings()

        return template.render(
            report=report,
            company_name=report.company_name,
            company_url=report.company_url,
            overall_score=report.overall_percentage,
            overall_grade=report.overall_grade.value,
            modules=report.modules,
            recommendations=report.get_all_recommendations()[:max_recs],
            quick_wins=report.get_quick_wins(max_highlights),
            strengths=report.get_top_strengths(max_highlights),
            critical_gaps=report.get_critical_gaps(max_highlights),
            company_profile=company_profile or {},
            logo_base64=logo_base64,
            embedded_font_css=embedded_font_css,
            has_screenshots=bool(screenshot_data),
            module_screenshots=module_screenshots,
            mockup_pairs=mockup_pairs,
            screenshot_diagnostic=screenshot_diagnostic,
            executive_narrative=executive_narrative,
            app_version=get_version(),
            # New report sections
            strategic_diagnosis=report.strategic_diagnosis,
            buyer_journey_analysis=report.buyer_journey_analysis,
            revenue_impact_model=report.revenue_impact_model,
            benchmarks=report.benchmarks,
            talk_track=report.talk_track,
            cmo_faq=report.cmo_faq,
            next_steps=report.next_steps_summary,
            annotated_screenshots=annotated_screenshots or [],
            # Consultant info
            consultant_name=getattr(settings, "consultant_name", "Bhavsar Growth Consulting"),
            consultant_bio=getattr(settings, "consultant_bio", ""),
        )

    def _process_screenshots(
        self, screenshots: dict, report: AuditReport
    ) -> tuple[dict, dict, list]:
        """Process raw screenshot data into template-friendly structures.

        Returns: (screenshot_data, module_screenshots, mockup_pairs)
        """
        screenshot_data = {}
        for key, ss in screenshots.items():
            if not ss.base64_data:
                continue
            screenshot_data[key] = {
                "base64": ss.base64_data,
                "description": ss.description,
                "type": ss.screenshot_type,
                "page_type": ss.page_type,
            }

        # Group screenshots by which modules should display them
        agent_screenshot_types = {
            "visual_design": {"full_page", "hero", "nav", "footer", "mobile_full"},
            "messaging": {"hero", "h1", "full_page"},
            "conversion": {"cta_primary", "form", "pricing"},
        }

        module_screenshots = {}
        for module in report.modules:
            agent = module.agent_name
            if agent not in agent_screenshot_types:
                continue
            allowed = agent_screenshot_types[agent]
            shots = []
            seen_types = set()
            for ss in screenshots.values():
                if ss.screenshot_type in allowed and ss.base64_data and ss.screenshot_type not in seen_types:
                    shots.append({
                        "base64": ss.base64_data,
                        "description": ss.description,
                        "type": ss.screenshot_type,
                    })
                    seen_types.add(ss.screenshot_type)
                    if len(shots) >= 4:
                        break
            if shots:
                module_screenshots[agent] = shots

        # Build before/after mockup pairs
        mockup_pairs = []
        mockups = [ss for ss in screenshots.values() if ss.mockup_for and ss.base64_data]
        for mockup in mockups:
            # Find an "original" screenshot to pair with (hero or h1 from homepage)
            before_b64 = ""
            for ss in screenshots.values():
                if ss.screenshot_type in ("hero", "h1") and ss.page_type == "home" and ss.base64_data:
                    before_b64 = ss.base64_data
                    break
            # Fallback to full page if no hero/h1
            if not before_b64:
                for ss in screenshots.values():
                    if ss.screenshot_type == "full_page" and ss.page_type == "home" and ss.base64_data:
                        before_b64 = ss.base64_data
                        break

            mockup_pairs.append({
                "label": mockup.description.replace("Mockup: ", ""),
                "before_base64": before_b64,
                "before_label": "Current",
                "after_base64": mockup.base64_data,
                "after_label": "Suggested",
            })

        return screenshot_data, module_screenshots, mockup_pairs

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

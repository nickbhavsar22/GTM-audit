"""Report Generation Agent — synthesizes all agent findings into HTML/Markdown report."""

import json
import logging
import secrets
from datetime import datetime
from typing import Any

from agents.base_agent import BaseAgent
from config.constants import AGENT_DISPLAY_NAMES, AgentName, score_to_grade
from reports.scoring import (
    AuditReport,
    Effort,
    Impact,
    ModuleScore,
    Recommendation,
    ScoreItem,
)

logger = logging.getLogger(__name__)

# Agents that produce scored modules (not web_scraper or company_research)
SCORED_AGENTS = [
    AgentName.SEO,
    AgentName.MESSAGING,
    AgentName.VISUAL_DESIGN,
    AgentName.COMPETITOR,
    AgentName.REVIEW_SENTIMENT,
    AgentName.CONVERSION,
    AgentName.SOCIAL,
    AgentName.ICP,
]


class ReportAgent(BaseAgent):
    agent_name = "report"
    agent_display_name = "Report Generation"
    dependencies = []  # Will run after all others via orchestrator ordering

    async def run(self) -> dict[str, Any]:
        """Synthesize all agent results into a comprehensive report."""
        await self.update_progress(10, "Collecting agent results")

        # Build AuditReport from all agent analyses
        report = AuditReport(
            company_name=self.context.company_name or "Unknown Company",
            company_url=self.context.company_url,
            audit_type=self.context.audit_type,
            audit_date=datetime.utcnow().strftime("%Y-%m-%d"),
        )

        # Add company profile as first module (non-scored)
        company_data = self.context.get_analysis("company_research")
        if company_data and company_data.get("status") == "completed":
            await self.update_progress(20, "Processing company research")
            profile_module = ModuleScore(
                name="Company Profile & Context",
                agent_name="company_research",
                analysis_text=company_data.get("analysis_text", ""),
            )
            report.modules.append(profile_module)

        # Process each scored agent's results
        await self.update_progress(30, "Processing agent analyses")
        for agent_name in SCORED_AGENTS:
            analysis = self.context.get_analysis(agent_name.value)
            if not analysis or analysis.get("status") != "completed":
                continue

            display_name = AGENT_DISPLAY_NAMES.get(agent_name, agent_name.value)
            module = self._build_module_score(agent_name.value, display_name, analysis)
            report.modules.append(module)

        await self.update_progress(60, "Rendering HTML report")

        # Render HTML
        from reports.renderer import ReportRenderer

        renderer = ReportRenderer()
        html_content = renderer.render_html(report)

        await self.update_progress(75, "Generating Markdown export")

        # Generate Markdown
        markdown_content = self._generate_markdown(report)

        await self.update_progress(85, "Saving report to database")

        # Save to database
        if self.db:
            self._save_report(html_content, markdown_content, report)

        # Update audit overall score
        if self.db and report.modules:
            self._update_audit_score(report)

        return {
            "score": report.overall_percentage,
            "grade": report.overall_grade.value,
            "analysis_text": (
                f"Report generated with {len(report.modules)} sections "
                f"and {len(report.get_all_recommendations())} recommendations. "
                f"Overall GTM score: {report.overall_percentage:.0f}/100 "
                f"({report.overall_grade.value})."
            ),
            "recommendations": [],
            "result_data": {
                "sections": len(report.modules),
                "total_recommendations": len(report.get_all_recommendations()),
                "overall_score": report.overall_percentage,
                "overall_grade": report.overall_grade.value,
            },
        }

    def _build_module_score(
        self, agent_name: str, display_name: str, analysis: dict
    ) -> ModuleScore:
        """Convert an agent's raw analysis into a ModuleScore."""
        result_data = analysis.get("result_data", {})

        module = ModuleScore(
            name=display_name,
            agent_name=agent_name,
            analysis_text=analysis.get("analysis_text", ""),
        )

        # Extract score items if present
        score_items = result_data.get("score_items", [])
        for item in score_items:
            module.items.append(
                ScoreItem(
                    name=item.get("name", ""),
                    score=item.get("score", 0),
                    max_score=item.get("max_score", 100),
                    weight=item.get("weight", 1.0),
                    notes=item.get("notes", ""),
                )
            )

        # If no score items but raw score is present, create a single item
        if not module.items and analysis.get("score") is not None:
            module.items.append(
                ScoreItem(
                    name=display_name,
                    score=analysis["score"],
                    max_score=100,
                )
            )

        # Extract recommendations
        raw_recs = analysis.get("recommendations", []) or result_data.get(
            "recommendations", []
        )
        for rec in raw_recs:
            if isinstance(rec, dict):
                module.recommendations.append(
                    Recommendation(
                        area=display_name,
                        issue=rec.get("issue", ""),
                        recommendation=rec.get("recommendation", ""),
                        current_state=rec.get("current_state", ""),
                        best_practice=rec.get("best_practice", ""),
                        impact=Impact(rec.get("impact", "Medium")),
                        effort=Effort(rec.get("effort", "Medium")),
                        implementation_steps=rec.get("implementation_steps", []),
                        success_metrics=rec.get("success_metrics", []),
                        timeline=rec.get("timeline", ""),
                    )
                )

        # Extract strengths/weaknesses
        module.strengths = result_data.get("strengths", [])
        module.weaknesses = result_data.get("weaknesses", [])

        return module

    def _generate_markdown(self, report: AuditReport) -> str:
        """Generate a Markdown version of the report."""
        lines = [
            f"# GTM Audit Report: {report.company_name}",
            f"**URL:** {report.company_url}",
            f"**Date:** {report.audit_date}",
            f"**Type:** {report.audit_type.capitalize()} Audit",
            f"**Overall Score:** {report.overall_percentage:.0f}/100 ({report.overall_grade.value})",
            "",
            "---",
            "",
            "## Executive Summary",
            "",
        ]

        # Quick wins
        quick_wins = report.get_quick_wins(5)
        if quick_wins:
            lines.append("### Quick Wins")
            for qw in quick_wins:
                lines.append(f"- **{qw.area}:** {qw.issue} — {qw.recommendation}")
            lines.append("")

        # Module sections
        for module in report.modules:
            lines.append(f"## {module.name}")
            if module.items:
                lines.append(
                    f"**Score:** {module.percentage:.0f}% | "
                    f"**Grade:** {module.grade.value}"
                )
            lines.append("")

            if module.analysis_text:
                lines.append(module.analysis_text)
                lines.append("")

            if module.strengths:
                lines.append("### Strengths")
                for s in module.strengths:
                    lines.append(f"- {s}")
                lines.append("")

            if module.weaknesses:
                lines.append("### Areas for Improvement")
                for w in module.weaknesses:
                    lines.append(f"- {w}")
                lines.append("")

            if module.recommendations:
                lines.append("### Recommendations")
                for rec in module.recommendations:
                    lines.append(
                        f"- **{rec.issue}**: {rec.recommendation} "
                        f"(Impact: {rec.impact.value}, Effort: {rec.effort.value})"
                    )
                lines.append("")

            lines.append("---")
            lines.append("")

        # Prioritized action plan
        all_recs = report.get_all_recommendations()[:20]
        if all_recs:
            lines.append("## Prioritized Action Plan")
            lines.append("")
            for i, rec in enumerate(all_recs, 1):
                lines.append(
                    f"{i}. **[{rec.area}]** {rec.issue} — "
                    f"{rec.recommendation} "
                    f"(Impact: {rec.impact.value}, Effort: {rec.effort.value})"
                )
            lines.append("")

        lines.append("---")
        lines.append(
            f"*Generated by GTM Audit Platform — Bhavsar Growth Consulting — {report.audit_date}*"
        )

        return "\n".join(lines)

    def _save_report(
        self, html_content: str, markdown_content: str, report: AuditReport
    ) -> None:
        """Save the generated report to the database."""
        try:
            from backend.models.report import Report

            share_token = secrets.token_urlsafe(32)
            db_report = Report(
                audit_id=self.context.audit_id,
                html_content=html_content,
                markdown_content=markdown_content,
                share_token=share_token,
                report_metadata={
                    "sections": len(report.modules),
                    "recommendations": len(report.get_all_recommendations()),
                    "overall_score": report.overall_percentage,
                    "overall_grade": report.overall_grade.value,
                },
            )
            self.db.add(db_report)
            self.db.commit()
            logger.info(f"Report saved with share token: {share_token}")
        except Exception as e:
            logger.error(f"Failed to save report: {e}")

    def _update_audit_score(self, report: AuditReport) -> None:
        """Update the audit record with the overall score."""
        try:
            from backend.models.audit import Audit

            audit = (
                self.db.query(Audit)
                .filter(Audit.id == self.context.audit_id)
                .first()
            )
            if audit:
                audit.overall_score = report.overall_percentage
                audit.overall_grade = report.overall_grade.value
                audit.company_name = report.company_name
                self.db.commit()
        except Exception as e:
            logger.error(f"Failed to update audit score: {e}")

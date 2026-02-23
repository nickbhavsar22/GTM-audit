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

# Industry median benchmarks for score context (B2B SaaS)
INDUSTRY_BENCHMARKS = {
    "seo": 68,
    "messaging": 62,
    "visual_design": 65,
    "competitor": 60,
    "review_sentiment": 55,
    "conversion": 58,
    "social": 50,
    "icp": 55,
}


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

        # If no analysis modules ran, add an error explanation
        scored_modules = [m for m in report.modules if m.agent_name != "company_research"]
        if not scored_modules:
            web_scraper_result = self.context.get_analysis("web_scraper")
            error_detail = ""
            if not web_scraper_result:
                error_detail = "The web scraper did not produce any results."
            elif web_scraper_result.get("status") == "failed":
                error_detail = (
                    f"The web scraper failed: {web_scraper_result.get('error', 'unknown error')}. "
                )
            else:
                error_detail = "The web scraper completed but downstream agents could not run."

            report.modules.append(ModuleScore(
                name="Audit Incomplete",
                agent_name="error",
                analysis_text=(
                    f"The audit of {self.context.company_url} could not be completed. "
                    f"{error_detail} "
                    f"This may be due to the site blocking automated access, network issues, "
                    f"or missing browser dependencies. Please verify the URL and try again."
                ),
            ))

        # Generate visual mockups for top recommendations
        await self.update_progress(40, "Generating visual mockups")
        await self._generate_mockups(report)

        # Generate executive narrative via LLM
        await self.update_progress(43, "Writing executive narrative")
        executive_narrative = await self._generate_executive_narrative(report, company_data)

        # Generate strategic diagnosis
        await self.update_progress(46, "Writing strategic diagnosis")
        report.strategic_diagnosis = await self._generate_strategic_diagnosis(report, company_data)

        # Generate buyer journey analysis
        await self.update_progress(49, "Analyzing buyer journey")
        report.buyer_journey_analysis = await self._generate_buyer_journey_analysis(report, company_data)

        # Generate revenue impact model
        await self.update_progress(52, "Building revenue impact model")
        report.revenue_impact_model = await self._generate_revenue_impact_model(report, company_data)

        # Generate benchmark examples
        await self.update_progress(55, "Researching benchmark examples")
        report.benchmarks = await self._generate_benchmarks(report, company_data)

        # Generate module callouts
        await self.update_progress(58, "Generating key insights")
        await self._generate_module_callouts(report)

        # Enrich recommendations with owner, effort estimate, rationale
        await self.update_progress(60, "Enriching action plan")
        await self._enrich_recommendations(report)

        # Generate readout materials (talk track, CMO FAQ, next steps)
        await self.update_progress(61, "Generating readout materials")
        await self._generate_readout_materials(report, company_data)

        # Generate annotated screenshots
        await self.update_progress(63, "Annotating screenshots")
        annotated_screenshots = await self._generate_annotated_screenshots(report)

        await self.update_progress(65, "Rendering HTML report")

        # Gather company profile for template
        company_profile = None
        if company_data and company_data.get("status") == "completed":
            company_profile = company_data.get("result_data", {})

        # Render HTML with screenshots
        from reports.renderer import ReportRenderer

        renderer = ReportRenderer()
        html_content = renderer.render_html(
            report,
            company_profile=company_profile,
            screenshots=dict(self.context.screenshots),
            screenshot_diagnostic=self.context.screenshot_diagnostic,
            executive_narrative=executive_narrative,
            annotated_screenshots=annotated_screenshots,
        )

        await self.update_progress(75, "Generating Markdown export")

        # Generate Markdown
        markdown_content = self._generate_markdown(report)

        await self.update_progress(85, "Saving report to database")

        # Save to database
        if not self.db:
            raise RuntimeError("Report agent requires a database session to save the report")
        self._save_report(html_content, markdown_content, report)

        # Update audit overall score
        if report.modules:
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

    async def _generate_mockups(self, report: AuditReport) -> None:
        """Generate visual mockups for top headline/CTA recommendations."""
        from config.settings import get_settings
        settings = get_settings()

        if not settings.mockup_generation_enabled:
            return

        # Find headline-related recommendations from messaging module
        headline_recs = [
            r for r in report.get_all_recommendations()
            if any(kw in r.issue.lower() for kw in ("headline", "value prop", "h1", "tagline"))
        ]

        if not headline_recs:
            return

        try:
            from agents.mockup_generator import MockupGenerator

            generator = MockupGenerator(self.context)

            for i, rec in enumerate(headline_recs[:2]):
                # Use the recommendation text as the suggested headline
                suggested = rec.recommendation
                # Truncate to reasonable headline length
                if len(suggested) > 120:
                    suggested = suggested[:117] + "..."

                html = generator.generate_headline_mockup_html(
                    suggested_h1=suggested,
                )
                await generator.generate_and_screenshot_mockup(
                    html,
                    mockup_name=f"headline_mockup_{i}",
                    recommendation_ref=rec.issue,
                )
                logger.info(f"Generated mockup for: {rec.issue[:60]}")

        except Exception as e:
            logger.warning(f"Mockup generation failed (non-critical): {e}")

    async def _generate_executive_narrative(
        self, report: AuditReport, company_data: dict | None
    ) -> str:
        """Generate a strategic executive narrative using LLM."""
        if not self.llm:
            return ""

        # Gather module summaries
        module_summaries = []
        for m in report.modules:
            if m.items:
                benchmark_ctx = ""
                if m.benchmark:
                    benchmark_ctx = f" (B2B SaaS median: {m.benchmark}%)"
                module_summaries.append(
                    f"- {m.name}: {m.percentage:.0f}%{benchmark_ctx} — {m.analysis_text[:300]}"
                )

        company_context = ""
        if company_data and company_data.get("status") == "completed":
            company_context = company_data.get("analysis_text", "")[:1500]

        quick_wins = report.get_quick_wins(3)
        qw_text = "\n".join(f"- {r.area}: {r.issue}" for r in quick_wins) if quick_wins else "None identified"

        critical_gaps = report.get_critical_gaps(3)
        gaps_text = "\n".join(critical_gaps) if critical_gaps else "None identified"

        prompt = f"""Write a 400-500 word executive summary for a GTM diagnostic audit report. This is a $3,000 deliverable read by a CMO or VP Marketing.

COMPANY CONTEXT:
{company_context}

WEBSITE: {report.company_url}

MODULE SCORES:
{chr(10).join(module_summaries)}

OVERALL SCORE: {report.overall_percentage:.0f}/100 ({report.overall_grade.value})

TOP QUICK WINS:
{qw_text}

CRITICAL GAPS:
{gaps_text}

STRUCTURE (follow this exact order):
1. THE SITUATION (2-3 sentences): What {report.company_name} has built and why it matters. Show you understand the business.
2. THE CORE STRATEGIC DIAGNOSIS (2-3 sentences): The single most important GTM problem, stated plainly. Not a list of issues — one root cause.
3. THE EVIDENCE (3-4 sentences): The 2-3 most damaging specific findings that prove the diagnosis. Use their actual page URLs, product names, and competitor names.
4. THE OPPORTUNITY (2-3 sentences): What becomes possible if this is fixed. Be credible and conservative — no inflated pipeline claims without showing math.
5. THE RECOMMENDED PATH (1-2 sentences): What to do first and why.

RULES:
- Prose only. NO bullet points in this section.
- Every sentence must be specific to {report.company_name}. If a sentence could apply to any company, rewrite it.
- Use their actual product names, market terminology, and competitor names.
- No generic consulting language ("leverage", "optimize", "unlock").
- Be direct. A CMO is reading this and evaluating whether you understand their business.
Do NOT start with "Executive Summary" or any header. Write the paragraphs directly."""

        system = (
            "You are a senior B2B marketing consultant with 20+ years experience writing an executive "
            "summary for a premium GTM diagnostic audit. Write like someone who has run marketing at a "
            "company like this, not someone who crawled their website. Be direct and specific. Avoid "
            "generic consulting language. The buyer is a sophisticated CMO evaluating whether this "
            "consultant understands their business."
        )

        try:
            return await self.call_llm(prompt, system=system)
        except Exception as e:
            logger.warning(f"Executive narrative generation failed: {e}")
            return ""

    async def _generate_strategic_diagnosis(
        self, report: AuditReport, company_data: dict | None
    ) -> str:
        """Generate a 3-5 paragraph strategic diagnosis — the most important section."""
        if not self.llm:
            return ""

        findings = []
        for m in report.modules:
            if m.items:
                findings.append(
                    f"- {m.name} ({m.percentage:.0f}%): {m.analysis_text[:400]}"
                )
                if m.weaknesses:
                    findings.append(f"  Key gaps: {'; '.join(m.weaknesses[:3])}")

        company_context = ""
        if company_data and company_data.get("status") == "completed":
            rd = company_data.get("result_data", {})
            company_context = (
                f"Company: {rd.get('company_name', report.company_name)}\n"
                f"Industry: {rd.get('industry', 'Unknown')}\n"
                f"Category: {rd.get('category', 'Unknown')}\n"
                f"Target: {rd.get('target_market', 'Unknown')}\n"
                f"Value Prop: {rd.get('value_proposition', 'Unknown')}\n"
                f"Competitors: {', '.join(rd.get('competitive_context', {}).get('likely_competitors', []))}\n"
            )

        prompt = f"""Write a strategic diagnosis for {report.company_name}'s go-to-market execution.

COMPANY:
{company_context}

ALL FINDINGS:
{chr(10).join(findings)}

INSTRUCTIONS:
This is 3-5 paragraphs of narrative analysis that could ONLY apply to {report.company_name}. It answers: "If you could only tell this CMO one thing, what would it be?"

- Connect the tactical findings to a coherent strategic problem
- Identify the ROOT CAUSE that explains multiple symptoms
- Use {report.company_name}'s own language, product names, and market context
- Write in the voice of a senior B2B marketing consultant with 20+ years experience
- Avoid generic consulting language ("leverage", "optimize", "synergize")
- Be direct. Every paragraph must pass the test: "Could this have been written about a different company?" If yes, rewrite it.
- No bullet points. Prose only.
- Do NOT include any headers or titles. Just write the paragraphs."""

        system = (
            "You are a senior B2B marketing consultant writing a strategic diagnosis. "
            "You've done 200+ audits for B2B SaaS companies. Write with authority and specificity. "
            "Your diagnosis should feel like it was written by someone who has run marketing at a "
            "company like this one."
        )

        try:
            return await self.call_llm(prompt, system=system)
        except Exception as e:
            logger.warning(f"Strategic diagnosis generation failed: {e}")
            return ""

    async def _generate_buyer_journey_analysis(
        self, report: AuditReport, company_data: dict | None
    ) -> str:
        """Generate a 1-page buyer journey analysis."""
        if not self.llm:
            return ""

        conversion_data = self.context.get_analysis("conversion")
        competitor_data = self.context.get_analysis("competitor")

        buyer_journey_ctx = ""
        if conversion_data and conversion_data.get("status") == "completed":
            rd = conversion_data.get("result_data", {})
            bj = rd.get("buyer_journey", {})
            if bj:
                buyer_journey_ctx = (
                    f"Primary path: {' → '.join(bj.get('primary_path', []))}\n"
                    f"Clicks to conversion: {bj.get('clicks_to_conversion', 'unknown')}\n"
                    f"Friction points: {'; '.join(bj.get('friction_points', []))}\n"
                )

        company_context = ""
        if company_data and company_data.get("status") == "completed":
            rd = company_data.get("result_data", {})
            ta = rd.get("target_audience", {})
            company_context = (
                f"Target industries: {', '.join(ta.get('industries', []))}\n"
                f"Target roles: {', '.join(ta.get('roles', []))}\n"
                f"Primary buyer: {ta.get('primary_buyer', 'Unknown')}\n"
                f"Pricing model: {rd.get('business_model', {}).get('pricing_model', 'Unknown')}\n"
            )

        competitor_names = ""
        if competitor_data and competitor_data.get("status") == "completed":
            comps = competitor_data.get("result_data", {}).get("competitors", [])
            competitor_names = ", ".join(c.get("name", "") for c in comps[:5])

        prompt = f"""Write a 1-page buyer journey analysis for {report.company_name}.

COMPANY CONTEXT:
{company_context}

CURRENT CONVERSION DATA:
{buyer_journey_ctx}

COMPETITORS: {competitor_names}
WEBSITE: {report.company_url}

Cover these topics in 3-4 paragraphs:
1. Where the target buyer starts their search for a solution like {report.company_name}'s
2. What they read and trust during evaluation (review sites, analyst reports, peers, content)
3. Who influences the buying decision and what objections they carry
4. Where {report.company_name}'s current GTM motion intercepts these buyers — and where it misses them entirely

This makes CMOs feel like you understand their customer, which is the highest-value signal you can send.

RULES:
- Prose only, no bullets
- Be specific to this company's market and buyer
- No generic advice
- Do NOT include headers or titles"""

        system = (
            "You are a senior B2B marketing consultant analyzing the buyer journey. "
            "Write with deep understanding of how B2B buyers actually research and purchase."
        )

        try:
            return await self.call_llm(prompt, system=system)
        except Exception as e:
            logger.warning(f"Buyer journey analysis generation failed: {e}")
            return ""

    async def _generate_revenue_impact_model(
        self, report: AuditReport, company_data: dict | None
    ) -> dict:
        """Generate a transparent revenue impact model with conservative/aggressive scenarios."""
        if not self.llm:
            return {}

        seo_data = self.context.get_analysis("seo")
        conversion_data = self.context.get_analysis("conversion")

        data_context = f"Website: {report.company_url}\n"
        data_context += f"Pages crawled: {len(self.context.pages)}\n"

        if seo_data and seo_data.get("status") == "completed":
            data_context += f"SEO score: {seo_data.get('score', 'N/A')}/100\n"

        if conversion_data and conversion_data.get("status") == "completed":
            data_context += f"Conversion score: {conversion_data.get('score', 'N/A')}/100\n"
            rd = conversion_data.get("result_data", {})
            bj = rd.get("buyer_journey", {})
            data_context += f"Clicks to conversion: {bj.get('clicks_to_conversion', 'N/A')}\n"

        prompt = f"""Create a revenue impact model for {report.company_name}. Return ONLY valid JSON.

DATA:
{data_context}

Return this exact JSON structure:
{{
    "baseline": {{
        "monthly_traffic_estimate": "<number or range>",
        "estimated_conversion_rate": "<percentage>",
        "estimated_monthly_leads": "<number or range>",
        "assumed_close_rate": "<percentage>",
        "assumed_acv": "<dollar amount>",
        "estimated_monthly_pipeline": "<dollar amount>"
    }},
    "conservative": {{
        "scenario_label": "50% of Recommendations Executed",
        "traffic_change": "<percentage improvement>",
        "conversion_change": "<percentage improvement>",
        "monthly_leads_change": "<number>",
        "monthly_pipeline_change": "<dollar amount>",
        "annual_impact": "<dollar amount>"
    }},
    "aggressive": {{
        "scenario_label": "Full Execution",
        "traffic_change": "<percentage improvement>",
        "conversion_change": "<percentage improvement>",
        "monthly_leads_change": "<number>",
        "monthly_pipeline_change": "<dollar amount>",
        "annual_impact": "<dollar amount>"
    }},
    "methodology_note": "Brief explanation of assumptions and how estimates were derived. Be transparent that these are directional estimates based on observed patterns, not guarantees."
}}

RULES:
- Label ALL numbers as estimates
- Be conservative — it's better to under-promise
- Show your reasoning in the methodology note
- Use ranges where appropriate (e.g., "$50K-$100K")"""

        try:
            response = await self.call_llm_json(prompt)
            result = self.parse_json(response)
            return result or {}
        except Exception as e:
            logger.warning(f"Revenue impact model generation failed: {e}")
            return {}

    async def _generate_benchmarks(
        self, report: AuditReport, company_data: dict | None
    ) -> list[dict]:
        """Generate 'What Good Looks Like' benchmark examples per category."""
        if not self.llm:
            return []

        categories = []
        for m in report.modules:
            if m.items and m.weaknesses:
                categories.append(f"- {m.name}: Top issues: {'; '.join(m.weaknesses[:2])}")

        if not categories:
            return []

        prompt = f"""For each category below, provide one brief example of a B2B SaaS company that executes well in this area and explain why (2-3 sentences each). Return ONLY valid JSON.

CATEGORIES:
{chr(10).join(categories)}

COMPANY BEING AUDITED: {report.company_name} ({report.company_url})

Return this JSON:
[
    {{
        "category": "<module name>",
        "example_company": "<named company>",
        "description": "<2-3 sentences explaining what they do well and why it works>"
    }}
]

Use real, named B2B SaaS companies that a CMO would recognize. These should be companies in adjacent or comparable markets."""

        try:
            response = await self.call_llm_json(prompt)
            result = self.parse_json(response)
            return result if isinstance(result, list) else []
        except Exception as e:
            logger.warning(f"Benchmark generation failed: {e}")
            return []

    async def _generate_module_callouts(self, report: AuditReport) -> None:
        """Generate 'The Single Most Important Thing' callout for each scored module."""
        if not self.llm:
            return

        scored_modules = [m for m in report.modules if m.items]
        if not scored_modules:
            return

        module_summaries = []
        for m in scored_modules:
            module_summaries.append(
                f"- {m.name} ({m.percentage:.0f}%): "
                f"Strengths: {'; '.join(m.strengths[:2])}. "
                f"Weaknesses: {'; '.join(m.weaknesses[:2])}."
            )

        prompt = f"""For each analysis module below, write ONE sentence that captures the single most important insight a CMO needs to know. Return ONLY valid JSON.

COMPANY: {report.company_name}

MODULES:
{chr(10).join(module_summaries)}

Return this JSON:
{{
    "<module_name>": "<one sentence — direct, specific, actionable>"
}}

RULES:
- Each callout is exactly 1 sentence
- Must be specific to {report.company_name}
- Frame in terms of business impact, not technical details
- Be direct — these are for executives who skim"""

        try:
            response = await self.call_llm_json(prompt)
            result = self.parse_json(response)
            if result and isinstance(result, dict):
                for m in scored_modules:
                    m.callout = result.get(m.name, "")
        except Exception as e:
            logger.warning(f"Module callout generation failed: {e}")

    async def _enrich_recommendations(self, report: AuditReport) -> None:
        """Add owner, effort estimate, dependencies, and rationale to recommendations."""
        if not self.llm:
            return

        all_recs = report.get_all_recommendations()[:20]
        if not all_recs:
            return

        rec_summaries = []
        for i, rec in enumerate(all_recs):
            rec_summaries.append(
                f"{i+1}. [{rec.area}] {rec.issue}: {rec.recommendation[:150]}"
            )

        prompt = f"""For each recommendation below, provide owner, effort estimate, dependencies, and strategic rationale. Return ONLY valid JSON.

COMPANY: {report.company_name}

RECOMMENDATIONS:
{chr(10).join(rec_summaries)}

Return this JSON array (one entry per recommendation, same order):
[
    {{
        "owner": "Marketing|Engineering|Content|Agency",
        "effort_estimate": "<specific: '2 hours', '1 day', '1 week', etc.>",
        "dependencies": ["<what must happen first>"],
        "strategic_rationale": "<1 sentence: why this matters for pipeline/revenue>"
    }}
]

RULES:
- owner: Who on the team should execute this
- effort_estimate: Concrete time estimate (hours or days), NOT vague "Low/Medium/High"
- dependencies: What needs to happen before this can start (empty list if none)
- strategic_rationale: Frame in terms of pipeline, revenue, or buyer behavior"""

        try:
            response = await self.call_llm_json(prompt)
            result = self.parse_json(response)
            if result and isinstance(result, list):
                for i, enrichment in enumerate(result):
                    if i < len(all_recs) and isinstance(enrichment, dict):
                        all_recs[i].owner = enrichment.get("owner", "")
                        all_recs[i].effort_estimate = enrichment.get("effort_estimate", "")
                        all_recs[i].dependencies = enrichment.get("dependencies", [])
                        all_recs[i].strategic_rationale = enrichment.get("strategic_rationale", "")
        except Exception as e:
            logger.warning(f"Recommendation enrichment failed: {e}")

    async def _generate_annotated_screenshots(self, report: AuditReport) -> list[dict]:
        """Use Claude Vision API to identify regions of interest and annotate screenshots."""
        annotated = []

        if not self.llm:
            return annotated

        # Get homepage screenshot
        homepage_shots = []
        for key, ss in self.context.screenshots.items():
            if ss.screenshot_type == "full_page" and ss.page_type == "home" and ss.base64_data:
                homepage_shots.append(ss)
                break

        if not homepage_shots:
            return annotated

        try:
            from agents.screenshot_annotator import annotate_screenshot_b64

            for ss in homepage_shots:
                # Ask Claude Vision to identify annotation regions
                prompt = (
                    f"Analyze this screenshot of {report.company_name}'s website. "
                    f"Identify 3-5 specific areas that need improvement. "
                    f"For each area, provide the approximate pixel coordinates (x, y, width, height) "
                    f"of the region, a short label (max 6 words), and whether it's a problem (red) "
                    f"or strength (green).\n\n"
                    f"Return ONLY valid JSON:\n"
                    f'[{{"x": 100, "y": 200, "width": 400, "height": 80, '
                    f'"label": "Weak value proposition", "color": "red"}}]'
                )

                vision_images = [{"base64": ss.base64_data, "media_type": "image/png"}]
                response = await self.call_llm_vision(prompt, vision_images)
                annotations = self.parse_json(response)

                if annotations and isinstance(annotations, list):
                    annotated_b64 = annotate_screenshot_b64(ss.base64_data, annotations)
                    annotated.append({
                        "base64": annotated_b64,
                        "description": f"Annotated homepage analysis — {report.company_name}",
                        "page_type": ss.page_type,
                        "annotations": annotations,
                    })

        except Exception as e:
            logger.warning(f"Screenshot annotation failed (non-critical): {e}")

        return annotated

    async def _generate_readout_materials(
        self, report: AuditReport, company_data: dict | None
    ) -> None:
        """Generate talk track, CMO FAQ, and next steps for the readout appendix."""
        if not self.llm:
            return

        all_recs = report.get_all_recommendations()[:10]
        rec_summary = "\n".join(
            f"- [{r.area}] {r.issue}: {r.recommendation[:100]}" for r in all_recs
        )

        company_context = ""
        if company_data and company_data.get("status") == "completed":
            company_context = company_data.get("analysis_text", "")[:800]

        diagnosis_excerpt = report.strategic_diagnosis[:500] if report.strategic_diagnosis else ""

        prompt = f"""Generate readout materials for presenting this GTM audit to {report.company_name}'s leadership. Return ONLY valid JSON.

COMPANY: {report.company_name} ({report.company_url})
OVERALL SCORE: {report.overall_percentage:.0f}/100

COMPANY CONTEXT:
{company_context}

STRATEGIC DIAGNOSIS EXCERPT:
{diagnosis_excerpt}

TOP RECOMMENDATIONS:
{rec_summary}

Return this exact JSON structure:
{{
    "talk_track": [
        "<bullet 1: opening — what we analyzed and why>",
        "<bullet 2-3: the core diagnosis>",
        "<bullet 4-7: key findings by area>",
        "<bullet 8-9: what good looks like>",
        "<bullet 10-11: recommended next steps>",
        "<bullet 12: closing — why act now>"
    ],
    "cmo_faq": [
        {{
            "question": "<anticipated CMO question>",
            "response": "<2-3 sentence response>"
        }}
    ],
    "next_steps": {{
        "sprint_title": "30-Day Quick Start Sprint",
        "week_1": "<what to do in week 1>",
        "week_2": "<what to do in week 2>",
        "week_3": "<what to do in week 3>",
        "week_4": "<what to do in week 4>",
        "success_metric": "<how to measure success after 30 days>"
    }}
}}

RULES:
- Talk track: 10-12 bullets for a verbal walkthrough of the report. Written as speaking notes, not reading notes.
- CMO FAQ: Top 5 questions a skeptical CMO would ask, with direct, honest responses
- Next steps: A concrete 30-day sprint broken into weekly milestones
- Be specific to {report.company_name} — no generic advice
- Frame everything in terms of pipeline and revenue impact"""

        try:
            response = await self.call_llm_json(prompt)
            result = self.parse_json(response)
            if result and isinstance(result, dict):
                report.talk_track = result.get("talk_track", [])
                report.cmo_faq = result.get("cmo_faq", [])
                report.next_steps_summary = result.get("next_steps", {})
        except Exception as e:
            logger.warning(f"Readout materials generation failed: {e}")

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
                        business_impact=rec.get("business_impact", ""),
                        before_example=rec.get("before_example", ""),
                        after_example=rec.get("after_example", ""),
                        impact=Impact(rec.get("impact", "Medium")),
                        effort=Effort(rec.get("effort", "Medium")),
                        implementation_steps=rec.get("implementation_steps", []),
                        success_metrics=rec.get("success_metrics", []),
                        timeline=rec.get("timeline", ""),
                        owner=rec.get("owner", ""),
                        effort_estimate=rec.get("effort_estimate", ""),
                        dependencies=rec.get("dependencies", []),
                        strategic_rationale=rec.get("strategic_rationale", ""),
                    )
                )

        # Extract strengths/weaknesses
        module.strengths = result_data.get("strengths", [])
        module.weaknesses = result_data.get("weaknesses", [])

        # Set industry benchmark
        module.benchmark = INDUSTRY_BENCHMARKS.get(agent_name, 0.0)

        # Carry agent-specific data for rich template rendering
        extra_keys = {
            "competitor": [
                "competitors", "market_gaps", "differentiation_opportunities",
                "positioning_map", "feature_comparison",
            ],
            "messaging": [
                "current_value_proposition", "messaging_pillars",
                "homepage_teardown", "message_collisions", "messaging_clarity_score",
                "suggested_value_proposition",
            ],
            "conversion": [
                "buyer_journey", "demo_page_teardown", "funnel_analysis", "ab_test_ideas",
            ],
            "icp": ["icp_definition", "buyer_personas"],
            "review_sentiment": ["sentiment_themes"],
            "social": ["platforms_detected", "content_assessment"],
        }
        for key in extra_keys.get(agent_name, []):
            if key in result_data:
                module.extra_data[key] = result_data[key]

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
        """Save the generated report to the database using a fresh session."""
        from backend.models.base import SessionLocal
        from backend.models.report import Report

        db = SessionLocal()
        try:
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
            db.add(db_report)
            db.commit()
            logger.info(f"Report saved with share token: {share_token}")
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to save report: {e}", exc_info=True)
            raise
        finally:
            db.close()

    def _update_audit_score(self, report: AuditReport) -> None:
        """Update the audit record with the overall score using a fresh session."""
        from backend.models.audit import Audit
        from backend.models.base import SessionLocal

        db = SessionLocal()
        try:
            audit = (
                db.query(Audit)
                .filter(Audit.id == self.context.audit_id)
                .first()
            )
            if audit:
                audit.overall_score = report.overall_percentage
                audit.overall_grade = report.overall_grade.value
                audit.company_name = report.company_name
                db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to update audit score: {e}", exc_info=True)
            raise
        finally:
            db.close()

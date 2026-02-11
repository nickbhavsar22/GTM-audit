"""Conversion Optimization Agent — analyzes CRO, forms, CTAs, trust signals, and funnel."""

import json
import logging
from typing import Any

from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

CRO_SYSTEM = """You are a conversion rate optimization (CRO) expert specializing in B2B SaaS websites.
Analyze the website's conversion elements including forms, CTAs, trust signals, social proof,
and overall conversion funnel. Reference specific pages and elements."""

CRO_PROMPT = """Analyze conversion optimization for this B2B SaaS website.

Website: {company_url}

SITE STRUCTURE:
{site_structure}

ALL CTAs FOUND:
{ctas}

ALL FORMS FOUND:
{forms}

KEY PAGES:
{key_pages}

Provide a JSON response:
{{
    "overall_score": <number 0-100>,
    "score_items": [
        {{"name": "CTA Effectiveness", "score": <0-100>, "max_score": 100, "weight": 1.8, "notes": "..."}},
        {{"name": "Form Optimization", "score": <0-100>, "max_score": 100, "weight": 1.5, "notes": "..."}},
        {{"name": "Trust Signal Implementation", "score": <0-100>, "max_score": 100, "weight": 1.3, "notes": "..."}},
        {{"name": "Conversion Funnel Clarity", "score": <0-100>, "max_score": 100, "weight": 1.5, "notes": "..."}},
        {{"name": "Social Proof Placement", "score": <0-100>, "max_score": 100, "weight": 1.2, "notes": "..."}},
        {{"name": "Friction Reduction", "score": <0-100>, "max_score": 100, "weight": 1.0, "notes": "..."}},
        {{"name": "Value Communication", "score": <0-100>, "max_score": 100, "weight": 1.0, "notes": "..."}}
    ],
    "funnel_analysis": {{
        "primary_cta": "the main conversion action",
        "secondary_ctas": ["other conversion paths"],
        "funnel_stages_identified": ["awareness", "consideration", "decision"],
        "missing_stages": ["any gaps in the funnel"]
    }},
    "strengths": ["3-5 CRO strengths"],
    "weaknesses": ["3-5 CRO weaknesses"],
    "recommendations": [
        {{
            "issue": "CRO issue",
            "recommendation": "optimization suggestion",
            "current_state": "current state",
            "best_practice": "CRO best practice",
            "impact": "High|Medium|Low",
            "effort": "High|Medium|Low",
            "implementation_steps": ["step 1", "step 2", "step 3"],
            "success_metrics": ["metric"],
            "timeline": "timeframe"
        }}
    ],
    "ab_test_ideas": ["3-5 A/B test ideas with hypotheses"],
    "analysis_summary": "2-3 paragraph CRO analysis"
}}"""


class ConversionAgent(BaseAgent):
    agent_name = "conversion"
    agent_display_name = "Conversion Optimization"
    dependencies = ["web_scraper"]

    async def run(self) -> dict[str, Any]:
        await self.update_progress(10, "Mapping conversion elements")

        site_structure = self._extract_site_structure()
        ctas = self._extract_all_ctas()
        forms = self._extract_all_forms()
        key_pages = self._extract_key_pages()

        await self.update_progress(40, "Analyzing conversion funnel with AI")

        prompt = CRO_PROMPT.format(
            company_url=self.context.company_url,
            site_structure=site_structure,
            ctas=ctas,
            forms=forms,
            key_pages=key_pages,
        )

        try:
            response = await self.call_llm(prompt, system=CRO_SYSTEM)
            result = self._parse_json(response)

            if not result:
                return self._fallback_result()

            await self.update_progress(85, "Compiling CRO report")

            return {
                "score": result.get("overall_score", 50),
                "grade": None,
                "analysis_text": result.get("analysis_summary", ""),
                "recommendations": result.get("recommendations", []),
                "result_data": {
                    "score_items": result.get("score_items", []),
                    "funnel_analysis": result.get("funnel_analysis", {}),
                    "ab_test_ideas": result.get("ab_test_ideas", []),
                    "strengths": result.get("strengths", []),
                    "weaknesses": result.get("weaknesses", []),
                    "recommendations": result.get("recommendations", []),
                },
            }
        except Exception as e:
            logger.error(f"CRO analysis failed: {e}")
            return self._fallback_result()

    def _extract_site_structure(self) -> str:
        page_types = {}
        for page in self.context.pages.values():
            pt = page.page_type or "other"
            page_types.setdefault(pt, []).append(page.url)
        lines = ["Site structure by page type:"]
        for pt, urls in page_types.items():
            lines.append(f"  {pt}: {len(urls)} pages")
            for url in urls[:3]:
                lines.append(f"    - {url}")
        return "\n".join(lines)

    def _extract_all_ctas(self) -> str:
        all_ctas = []
        for page in self.context.pages.values():
            for cta in page.ctas:
                all_ctas.append(
                    f"- [{page.page_type}] \"{cta.get('text', '')}\" -> {cta.get('href', '')}"
                )
        return "\n".join(all_ctas[:40]) or "No CTAs found."

    def _extract_all_forms(self) -> str:
        all_forms = []
        for page in self.context.pages.values():
            for form in page.forms:
                fields = form.get("fields", [])
                field_names = [f.get("name", f.get("type", "?")) for f in fields]
                all_forms.append(
                    f"- [{page.page_type}] {page.url}\n"
                    f"  Action: {form.get('action', 'N/A')}\n"
                    f"  Fields ({len(fields)}): {', '.join(field_names)}"
                )
        return "\n".join(all_forms[:15]) or "No forms found."

    def _extract_key_pages(self) -> str:
        """Get content from conversion-critical pages."""
        priority = ["home", "pricing", "demo", "contact", "product"]
        lines = []
        for pt in priority:
            pages = self.context.get_pages_by_type(pt)
            for page in pages[:2]:
                lines.append(f"\n--- {pt.upper()}: {page.url} ---")
                lines.append(f"H1: {', '.join(page.h1_tags) or 'NONE'}")
                lines.append(f"Content: {page.raw_text[:2000]}")
        return "\n".join(lines)[:15000]

    def _parse_json(self, text: str) -> dict | None:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            import re
            match = re.search(r"\{[\s\S]*\}", text)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
        return None

    def _fallback_result(self) -> dict[str, Any]:
        return {
            "score": 50,
            "grade": None,
            "analysis_text": "CRO analysis incomplete — LLM analysis unavailable.",
            "recommendations": [],
            "result_data": {"fallback": True, "strengths": [], "weaknesses": []},
        }

"""Messaging & Positioning Agent — analyzes value proposition, headlines, and messaging clarity."""

import json
import logging
from typing import Any

from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

MESSAGING_SYSTEM = """You are an expert B2B SaaS marketing strategist specializing in messaging,
positioning, and value propositions. Analyze website content for messaging effectiveness,
clarity, and target audience alignment. Reference specific examples from the content."""

MESSAGING_PROMPT = """Analyze this B2B SaaS company's messaging and positioning effectiveness.

Website: {company_url}
Company Name: {company_name}

HOMEPAGE & KEY PAGE CONTENT:
{content}

CTAs FOUND:
{ctas}

TESTIMONIALS:
{testimonials}

Provide a JSON response:
{{
    "overall_score": <number 0-100>,
    "score_items": [
        {{"name": "Value Proposition Clarity", "score": <0-100>, "max_score": 100, "weight": 2.0, "notes": "..."}},
        {{"name": "Headline Effectiveness", "score": <0-100>, "max_score": 100, "weight": 1.5, "notes": "..."}},
        {{"name": "Target Audience Alignment", "score": <0-100>, "max_score": 100, "weight": 1.5, "notes": "..."}},
        {{"name": "Messaging Hierarchy", "score": <0-100>, "max_score": 100, "weight": 1.0, "notes": "..."}},
        {{"name": "Proof Elements (Social Proof)", "score": <0-100>, "max_score": 100, "weight": 1.2, "notes": "..."}},
        {{"name": "CTA Clarity & Compelling", "score": <0-100>, "max_score": 100, "weight": 1.3, "notes": "..."}},
        {{"name": "Differentiation / USP", "score": <0-100>, "max_score": 100, "weight": 1.5, "notes": "..."}},
        {{"name": "Benefit vs Feature Balance", "score": <0-100>, "max_score": 100, "weight": 1.0, "notes": "..."}}
    ],
    "current_value_proposition": "their current value prop as stated on site",
    "messaging_pillars": ["list of key messaging pillars/themes identified"],
    "strengths": ["list of 3-5 messaging strengths"],
    "weaknesses": ["list of 3-5 messaging weaknesses"],
    "recommendations": [
        {{
            "issue": "specific messaging issue",
            "recommendation": "what to change",
            "current_state": "current messaging example",
            "best_practice": "B2B SaaS messaging best practice",
            "impact": "High|Medium|Low",
            "effort": "High|Medium|Low",
            "implementation_steps": ["step 1", "step 2", "step 3"],
            "success_metrics": ["metric 1"],
            "timeline": "timeframe"
        }}
    ],
    "analysis_summary": "2-3 paragraph messaging analysis"
}}

Generate 5-8 specific recommendations with real examples from the content."""


class MessagingAgent(BaseAgent):
    agent_name = "messaging"
    agent_display_name = "Messaging & Positioning"
    dependencies = ["web_scraper"]

    async def run(self) -> dict[str, Any]:
        await self.update_progress(10, "Extracting messaging data")

        content = self._extract_messaging_data()
        ctas = self._extract_ctas()
        testimonials = self._extract_testimonials()

        await self.update_progress(40, "Analyzing messaging with AI")

        prompt = MESSAGING_PROMPT.format(
            company_url=self.context.company_url,
            company_name=self.context.company_name or "Unknown",
            content=content,
            ctas=ctas,
            testimonials=testimonials,
        )

        try:
            response = await self.call_llm_json(prompt, system=MESSAGING_SYSTEM)
            result = self._parse_json(response)

            if not result:
                logger.error(f"Messaging JSON parse failed. Response preview: {response[:500]}")
                self._last_error = f"JSON parse failed. Response starts: {response[:200]}"
                return self._fallback_result()

            await self.update_progress(85, "Compiling messaging report")

            return {
                "score": result.get("overall_score", 50),
                "grade": None,
                "analysis_text": result.get("analysis_summary", ""),
                "recommendations": result.get("recommendations", []),
                "result_data": {
                    "score_items": result.get("score_items", []),
                    "strengths": result.get("strengths", []),
                    "weaknesses": result.get("weaknesses", []),
                    "current_value_proposition": result.get("current_value_proposition", ""),
                    "messaging_pillars": result.get("messaging_pillars", []),
                    "recommendations": result.get("recommendations", []),
                },
            }
        except Exception as e:
            logger.error(f"Messaging analysis failed: {e}")
            return self._fallback_result()

    def _extract_messaging_data(self) -> str:
        """Extract messaging-relevant content from key pages."""
        lines = []
        # Prioritize homepage and product pages
        priority_types = ["home", "product", "pricing", "about", "customers"]
        sorted_pages = sorted(
            self.context.pages.values(),
            key=lambda p: (
                priority_types.index(p.page_type)
                if p.page_type in priority_types
                else 99
            ),
        )

        for page in sorted_pages[:10]:
            lines.append(f"\n--- {page.page_type.upper()}: {page.url} ---")
            lines.append(f"Title: {page.title}")
            if page.h1_tags:
                lines.append(f"H1: {' | '.join(page.h1_tags)}")
            if page.h2_tags:
                lines.append(f"H2s: {' | '.join(page.h2_tags[:8])}")
            lines.append(f"Content:\n{page.raw_text[:3000]}")

        return "\n".join(lines)[:20000]

    def _extract_ctas(self) -> str:
        """Extract all CTAs from the site."""
        all_ctas = []
        for page in self.context.pages.values():
            for cta in page.ctas:
                text = cta.get("text", "").strip()
                if text and text not in all_ctas:
                    all_ctas.append(text)
        return "\n".join(f"- {cta}" for cta in all_ctas[:30])

    def _extract_testimonials(self) -> str:
        all_testimonials = []
        for page in self.context.pages.values():
            all_testimonials.extend(page.testimonials)
        if not all_testimonials:
            return "No testimonials found on the website."
        return "\n".join(f"- {t[:200]}" for t in all_testimonials[:10])

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
            "analysis_text": "Messaging analysis incomplete — LLM analysis unavailable.",
            "recommendations": [],
            "result_data": {"fallback": True, "strengths": [], "weaknesses": []},
        }

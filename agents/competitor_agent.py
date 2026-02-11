"""Competitor Intelligence Agent — identifies and analyzes 5-10 competitors."""

import json
import logging
from typing import Any

from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

COMPETITOR_SYSTEM = """You are a competitive intelligence analyst specializing in B2B SaaS markets.
Identify competitors based on the company's positioning and analyze competitive dynamics.
Be specific and reference actual company names when possible."""

COMPETITOR_PROMPT = """Analyze competitive positioning for this B2B SaaS company.

Website: {company_url}
Company Name: {company_name}

COMPANY PROFILE:
{company_profile}

WEBSITE CONTENT (key pages):
{content}

Tasks:
1. Identify 5-10 likely competitors based on the company's positioning, target market, and product category
2. For each competitor, describe their positioning and how they compare
3. Identify market gaps and differentiation opportunities

Provide a JSON response:
{{
    "overall_score": <number 0-100 based on competitive positioning strength>,
    "score_items": [
        {{"name": "Market Positioning Clarity", "score": <0-100>, "max_score": 100, "weight": 1.5, "notes": "..."}},
        {{"name": "Competitive Differentiation", "score": <0-100>, "max_score": 100, "weight": 2.0, "notes": "..."}},
        {{"name": "Feature/Benefit Communication", "score": <0-100>, "max_score": 100, "weight": 1.2, "notes": "..."}},
        {{"name": "Pricing Transparency", "score": <0-100>, "max_score": 100, "weight": 1.0, "notes": "..."}},
        {{"name": "Social Proof vs Competitors", "score": <0-100>, "max_score": 100, "weight": 1.0, "notes": "..."}}
    ],
    "competitors": [
        {{
            "name": "Competitor Name",
            "url": "competitor-url.com",
            "positioning": "their positioning statement",
            "strengths_vs_target": ["where they're stronger"],
            "weaknesses_vs_target": ["where target company is stronger"],
            "market_overlap": "High|Medium|Low"
        }}
    ],
    "market_gaps": ["opportunities not addressed by competitors"],
    "differentiation_opportunities": ["ways to differentiate further"],
    "strengths": ["3-5 competitive strengths"],
    "weaknesses": ["3-5 competitive weaknesses"],
    "recommendations": [
        {{
            "issue": "competitive challenge",
            "recommendation": "strategic response",
            "current_state": "current competitive position",
            "best_practice": "competitive best practice",
            "impact": "High|Medium|Low",
            "effort": "High|Medium|Low",
            "implementation_steps": ["step 1", "step 2", "step 3"],
            "success_metrics": ["metric"],
            "timeline": "timeframe"
        }}
    ],
    "analysis_summary": "2-3 paragraph competitive analysis"
}}"""


class CompetitorAgent(BaseAgent):
    agent_name = "competitor"
    agent_display_name = "Competitor Intelligence"
    dependencies = ["web_scraper"]

    async def run(self) -> dict[str, Any]:
        await self.update_progress(10, "Gathering competitive context")

        content = self.get_all_pages_content(max_chars=15000)

        # Use company profile if available
        company_profile = ""
        cp = self.context.get_analysis("company_research")
        if cp and cp.get("status") == "completed":
            company_profile = json.dumps(cp.get("result_data", {}), indent=2)[:5000]

        await self.update_progress(40, "Identifying competitors with AI")

        prompt = COMPETITOR_PROMPT.format(
            company_url=self.context.company_url,
            company_name=self.context.company_name or "Unknown",
            company_profile=company_profile or "Not available yet.",
            content=content,
        )

        try:
            response = await self.call_llm_json(prompt, system=COMPETITOR_SYSTEM)
            result = self._parse_json(response)

            if not result:
                logger.error(f"Competitor JSON parse failed. Response preview: {response[:500]}")
                self._last_error = f"JSON parse failed. Response starts: {response[:200]}"
                return self._fallback_result()

            # Store competitors in context for other agents
            self.context.competitors = result.get("competitors", [])

            await self.update_progress(85, "Compiling competitive report")

            return {
                "score": result.get("overall_score", 50),
                "grade": None,
                "analysis_text": result.get("analysis_summary", ""),
                "recommendations": result.get("recommendations", []),
                "result_data": {
                    "score_items": result.get("score_items", []),
                    "competitors": result.get("competitors", []),
                    "market_gaps": result.get("market_gaps", []),
                    "differentiation_opportunities": result.get(
                        "differentiation_opportunities", []
                    ),
                    "strengths": result.get("strengths", []),
                    "weaknesses": result.get("weaknesses", []),
                    "recommendations": result.get("recommendations", []),
                },
            }
        except Exception as e:
            logger.error(f"Competitor analysis failed: {e}")
            return self._fallback_result()

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
            "analysis_text": "Competitive analysis incomplete — LLM analysis unavailable.",
            "recommendations": [],
            "result_data": {
                "fallback": True,
                "competitors": [],
                "strengths": [],
                "weaknesses": [],
            },
        }

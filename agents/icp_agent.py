"""ICP & Segmentation Agent — defines buyer personas and market segments."""

import json
import logging
from typing import Any

from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

ICP_SYSTEM = """You are a B2B SaaS market segmentation and ICP (Ideal Customer Profile) strategist.
Analyze website content and company data to define target segments, buyer personas,
and ICP alignment. Be specific with evidence from the content."""

ICP_PROMPT = """Define the ICP and market segmentation for this B2B SaaS company.

Website: {company_url}
Company Name: {company_name}

COMPANY PROFILE:
{company_profile}

TESTIMONIALS & CUSTOMER EVIDENCE:
{customer_evidence}

KEY PAGE CONTENT:
{key_content}

Provide a JSON response:
{{
    "overall_score": <number 0-100 based on ICP clarity and targeting effectiveness>,
    "score_items": [
        {{"name": "ICP Definition Clarity", "score": <0-100>, "max_score": 100, "weight": 2.0, "notes": "..."}},
        {{"name": "Segment-Specific Messaging", "score": <0-100>, "max_score": 100, "weight": 1.5, "notes": "..."}},
        {{"name": "Buyer Persona Evidence", "score": <0-100>, "max_score": 100, "weight": 1.3, "notes": "..."}},
        {{"name": "Use Case Documentation", "score": <0-100>, "max_score": 100, "weight": 1.2, "notes": "..."}},
        {{"name": "Industry Targeting", "score": <0-100>, "max_score": 100, "weight": 1.0, "notes": "..."}},
        {{"name": "Company Size Targeting", "score": <0-100>, "max_score": 100, "weight": 1.0, "notes": "..."}}
    ],
    "icp_definition": {{
        "primary_icp": {{
            "company_size": "e.g., 50-500 employees",
            "industries": ["list of target industries"],
            "roles": ["key buyer roles"],
            "pain_points": ["main pain points addressed"],
            "use_cases": ["primary use cases"]
        }},
        "secondary_segments": [
            {{
                "segment_name": "name",
                "description": "description",
                "evidence": "evidence from website"
            }}
        ]
    }},
    "buyer_personas": [
        {{
            "title": "e.g., VP of Marketing",
            "goals": ["their goals"],
            "challenges": ["their challenges"],
            "messaging_alignment": "how well the site speaks to this persona"
        }}
    ],
    "strengths": ["3-5 ICP/segmentation strengths"],
    "weaknesses": ["3-5 ICP/segmentation weaknesses"],
    "recommendations": [
        {{
            "issue": "ICP/segmentation issue",
            "recommendation": "what to improve",
            "current_state": "current state",
            "best_practice": "segmentation best practice",
            "impact": "High|Medium|Low",
            "effort": "High|Medium|Low",
            "implementation_steps": ["step 1", "step 2"],
            "success_metrics": ["metric"],
            "timeline": "timeframe"
        }}
    ],
    "analysis_summary": "2-3 paragraph ICP/segmentation analysis"
}}"""


class ICPAgent(BaseAgent):
    agent_name = "icp"
    agent_display_name = "ICP & Segmentation"
    dependencies = ["web_scraper", "company_research"]

    async def run(self) -> dict[str, Any]:
        await self.update_progress(10, "Gathering customer evidence")

        company_profile = self._get_company_profile()
        customer_evidence = self._extract_customer_evidence()
        key_content = self._extract_key_content()

        await self.update_progress(40, "Defining ICP with AI")

        prompt = ICP_PROMPT.format(
            company_url=self.context.company_url,
            company_name=self.context.company_name or "Unknown",
            company_profile=company_profile,
            customer_evidence=customer_evidence,
            key_content=key_content,
        )

        try:
            response = await self.call_llm_json(prompt, system=ICP_SYSTEM)
            result = self.parse_json(response)

            if not result:
                return self._fallback_result()

            await self.update_progress(85, "Compiling ICP report")

            return {
                "score": result.get("overall_score", 50),
                "grade": None,
                "analysis_text": result.get("analysis_summary", ""),
                "recommendations": result.get("recommendations", []),
                "result_data": {
                    "score_items": result.get("score_items", []),
                    "icp_definition": result.get("icp_definition", {}),
                    "buyer_personas": result.get("buyer_personas", []),
                    "strengths": result.get("strengths", []),
                    "weaknesses": result.get("weaknesses", []),
                    "recommendations": result.get("recommendations", []),
                },
            }
        except Exception as e:
            logger.error(f"ICP analysis failed: {e}")
            return self._fallback_result()

    def _get_company_profile(self) -> str:
        cp = self.context.get_analysis("company_research")
        if cp and cp.get("status") == "completed":
            return json.dumps(cp.get("result_data", {}), indent=2)[:5000]
        return "Company profile not available."

    def _extract_customer_evidence(self) -> str:
        lines = []
        for page in self.context.pages.values():
            if page.testimonials:
                for t in page.testimonials:
                    lines.append(f"- [Testimonial] {t[:200]}")
            if page.page_type == "customers":
                lines.append(f"- [Customer page] {page.url}: {page.raw_text[:500]}")
        if not lines:
            return "No direct customer evidence found on the website."
        return "\n".join(lines[:20])

    def _extract_key_content(self) -> str:
        lines = []
        for pt in ["home", "product", "customers", "about"]:
            for page in self.context.get_pages_by_type(pt):
                lines.append(f"\n--- {pt.upper()}: {page.url} ---")
                lines.append(page.raw_text[:2000])
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
            "analysis_text": "ICP analysis incomplete — LLM analysis unavailable.",
            "recommendations": [],
            "result_data": {"fallback": True, "strengths": [], "weaknesses": []},
        }

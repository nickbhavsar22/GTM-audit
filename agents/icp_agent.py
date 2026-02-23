"""ICP & Segmentation Agent — defines buyer personas and market segments."""

import json
import logging
from typing import Any

from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

ICP_SYSTEM = """You are a B2B SaaS go-to-market strategist who specializes in ICP definition and buyer persona development. You don't just define segments — you assess how well the company's entire web presence aligns with the buyers they're trying to reach. You identify gaps between who they say they serve and how their website actually speaks to those buyers. Your analysis helps marketing teams focus resources on the segments where they can win."""

ICP_PROMPT = """Perform a comprehensive ICP and buyer persona assessment for this B2B SaaS company. Evaluate how well their website targets and speaks to their ideal buyers.

Website: {company_url}
Company Name: {company_name}

COMPANY PROFILE:
{company_profile}

TESTIMONIALS & CUSTOMER EVIDENCE:
{customer_evidence}

KEY PAGE CONTENT:
{key_content}

CRITICAL INSTRUCTIONS:
- For every finding, explain the BUSINESS IMPACT — how ICP clarity (or lack thereof) affects pipeline quality and conversion (e.g., "Trying to speak to both SMBs and enterprises on the same homepage dilutes the message for both, likely reducing qualified demo requests by 20-30%").
- Quote ACTUAL copy from the website that reveals targeting choices (or lack thereof).
- Assess the GAP between stated ICP and how the website actually communicates — do they say they target enterprise but their copy reads SMB?
- Compare to BEST PRACTICES with named examples of B2B SaaS companies with excellent ICP alignment.
- Write analysis_summary as a strategic narrative about go-to-market focus.

Provide a JSON response:
{{
    "overall_score": <number 0-100 based on ICP clarity and targeting effectiveness>,
    "score_items": [
        {{"name": "ICP Definition Clarity", "score": <0-100>, "max_score": 100, "weight": 2.0, "notes": "Can a visitor quickly tell if this product is for them?"}},
        {{"name": "Segment-Specific Messaging", "score": <0-100>, "max_score": 100, "weight": 1.5, "notes": "Does the site speak differently to different buyer segments?"}},
        {{"name": "Buyer Persona Evidence", "score": <0-100>, "max_score": 100, "weight": 1.3, "notes": "Are specific roles/titles addressed with relevant messaging?"}},
        {{"name": "Use Case Documentation", "score": <0-100>, "max_score": 100, "weight": 1.2, "notes": "Are use cases clearly articulated with outcomes?"}},
        {{"name": "Industry Targeting", "score": <0-100>, "max_score": 100, "weight": 1.0, "notes": "Are target industries named and supported with relevant content?"}},
        {{"name": "Company Size Targeting", "score": <0-100>, "max_score": 100, "weight": 1.0, "notes": "Is the company size targeting consistent across the site?"}}
    ],
    "icp_definition": {{
        "primary_icp": {{
            "company_size": "e.g., 50-500 employees — with evidence from the site",
            "industries": ["list of target industries with evidence"],
            "roles": ["key buyer roles with evidence from copy"],
            "pain_points": ["main pain points addressed — quote the copy"],
            "use_cases": ["primary use cases — quote the copy"],
            "evidence_strength": "strong|moderate|weak — how clearly is the ICP defined?"
        }},
        "secondary_segments": [
            {{
                "segment_name": "name",
                "description": "description",
                "evidence": "quoted evidence from website",
                "messaging_alignment": "how well the site speaks to this segment"
            }}
        ]
    }},
    "buyer_personas": [
        {{
            "title": "e.g., VP of Marketing",
            "seniority": "C-suite|VP|Director|Manager|Individual Contributor",
            "goals": ["their goals relevant to this product"],
            "challenges": ["their challenges this product addresses"],
            "messaging_alignment": "how well the site speaks to this persona with quoted evidence",
            "buyer_journey_support": "does the site provide content for this persona's evaluation process?"
        }}
    ],
    "icp_alignment_gaps": [
        {{
            "gap": "specific gap between stated ICP and website messaging",
            "evidence": "quoted copy showing the misalignment",
            "business_impact": "estimated effect on pipeline quality"
        }}
    ],
    "strengths": ["3-5 ICP/segmentation strengths with quoted evidence"],
    "weaknesses": ["3-5 ICP/segmentation weaknesses with business impact"],
    "recommendations": [
        {{
            "issue": "ICP/segmentation issue with quoted evidence",
            "recommendation": "what to improve",
            "business_impact": "estimated effect on pipeline quality or conversion",
            "before_example": "current messaging that misses the ICP",
            "after_example": "suggested ICP-aligned messaging",
            "current_state": "current state",
            "best_practice": "named example of a B2B SaaS company with excellent ICP alignment",
            "impact": "High|Medium|Low",
            "effort": "High|Medium|Low",
            "implementation_steps": ["step 1", "step 2"],
            "success_metrics": ["metric to track improvement"],
            "timeline": "timeframe"
        }}
    ],
    "analysis_summary": "3-4 paragraph strategic narrative about the company's ICP clarity and go-to-market focus. Frame how targeting decisions affect pipeline quality and conversion efficiency."
}}

Generate 5-8 specific, actionable ICP alignment recommendations."""


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
                    "icp_alignment_gaps": result.get("icp_alignment_gaps", []),
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

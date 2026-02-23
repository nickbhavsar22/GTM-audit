"""Review & Sentiment Agent — analyzes G2/Capterra reviews and customer sentiment."""

import json
import logging
from typing import Any

from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

REVIEW_SYSTEM = """You are a B2B trust and credibility strategist. You evaluate how effectively a company leverages customer proof to build buyer confidence and reduce purchase risk. You assess not just whether proof exists, but whether it's strategically deployed to support the buying journey. In B2B SaaS, the trust stack (testimonials, logos, case studies, reviews, security certifications) is often the difference between a demo request and a bounce. Your analysis reads like advice from a trusted GTM advisor."""

REVIEW_PROMPT = """Perform a comprehensive trust and credibility audit for this B2B SaaS company's website. Evaluate their entire "proof stack" — how effectively they use customer evidence to build buyer confidence.

Website: {company_url}
Company Name: {company_name}

TESTIMONIALS FROM WEBSITE:
{testimonials}

PROOF ELEMENTS (logos, metrics, awards):
{proof_elements}

MOCK REVIEW DATA (G2/Capterra estimates):
{review_data}

CRITICAL INSTRUCTIONS:
- For every finding, explain the BUSINESS IMPACT — how trust gaps affect conversion (e.g., "Having testimonials only on the homepage means visitors who reach the pricing page see no customer validation at their point of highest purchase anxiety, likely reducing demo requests by 10-20%").
- Quote ACTUAL testimonials and evaluate their effectiveness (named vs anonymous, specific vs generic, relevant to buyer persona).
- Compare to BEST PRACTICES with named examples of B2B SaaS companies with excellent trust stacks.
- Write analysis_summary as a strategic narrative about the company's credibility positioning.

Provide a JSON response:
{{
    "overall_score": <number 0-100>,
    "score_items": [
        {{"name": "Testimonial Quality & Specificity", "score": <0-100>, "max_score": 100, "weight": 1.5, "notes": "Are testimonials named, specific, and relevant to buyer personas?"}},
        {{"name": "Social Proof Strategic Placement", "score": <0-100>, "max_score": 100, "weight": 1.3, "notes": "Is proof placed near conversion points where anxiety is highest?"}},
        {{"name": "Customer Logo Credibility", "score": <0-100>, "max_score": 100, "weight": 1.0, "notes": "Are logos recognizable, relevant, and substantiated with stories?"}},
        {{"name": "Case Study Depth", "score": <0-100>, "max_score": 100, "weight": 1.2, "notes": "Do case studies show specific results with metrics?"}},
        {{"name": "Third-Party Validation", "score": <0-100>, "max_score": 100, "weight": 1.0, "notes": "G2 badges, awards, certifications, analyst mentions?"}},
        {{"name": "Trust Signal Effectiveness", "score": <0-100>, "max_score": 100, "weight": 1.0, "notes": "Overall assessment of the proof stack's persuasive power"}}
    ],
    "trust_stack_assessment": {{
        "testimonials_count": <number>,
        "named_testimonials": <number>,
        "testimonials_with_title": <number>,
        "testimonials_with_metrics": <number>,
        "client_logos_count": <number>,
        "case_studies_count": <number>,
        "third_party_badges": ["list of G2, SOC 2, etc."],
        "security_certifications": ["list of security badges"],
        "proof_near_ctas": true|false,
        "overall_trust_grade": "A|B|C|D|F"
    }},
    "sentiment_themes": {{
        "positive": ["positive themes with quoted evidence"],
        "negative": ["gaps or concerns with business impact"]
    }},
    "strengths": ["3-5 trust/credibility strengths with specific evidence"],
    "weaknesses": ["3-5 trust/credibility weaknesses with business impact estimates"],
    "recommendations": [
        {{
            "issue": "specific trust gap with evidence",
            "recommendation": "what to add or change",
            "business_impact": "estimated effect on conversion (e.g., 'adding named testimonials near the demo form typically increases submissions by 15-30%')",
            "before_example": "current state of proof on a specific page",
            "after_example": "suggested improvement with specifics",
            "current_state": "current state",
            "best_practice": "named example of a B2B SaaS company doing this well",
            "impact": "High|Medium|Low",
            "effort": "High|Medium|Low",
            "implementation_steps": ["step 1", "step 2"],
            "success_metrics": ["metric to track improvement"],
            "timeline": "timeframe"
        }}
    ],
    "analysis_summary": "3-4 paragraph strategic narrative about the company's trust and credibility positioning. Frame how their proof stack supports or undermines the buying journey."
}}

Generate 5-8 specific, actionable trust-building recommendations."""


class ReviewSentimentAgent(BaseAgent):
    agent_name = "review_sentiment"
    agent_display_name = "Reviews & Sentiment"
    dependencies = ["web_scraper"]

    async def run(self) -> dict[str, Any]:
        await self.update_progress(10, "Extracting testimonials")

        testimonials = self._extract_testimonials()
        proof_elements = self._extract_proof_elements()

        await self.update_progress(30, "Gathering review data")

        review_data = await self._get_mock_review_data()

        await self.update_progress(50, "Analyzing sentiment with AI")

        prompt = REVIEW_PROMPT.format(
            company_url=self.context.company_url,
            company_name=self.context.company_name or "Unknown",
            testimonials=testimonials,
            proof_elements=proof_elements,
            review_data=json.dumps(review_data, indent=2),
        )

        try:
            response = await self.call_llm_json(prompt, system=REVIEW_SYSTEM)
            result = self.parse_json(response)

            if not result:
                return self._fallback_result()

            await self.update_progress(85, "Compiling sentiment report")

            return {
                "score": result.get("overall_score", 50),
                "grade": None,
                "analysis_text": result.get("analysis_summary", ""),
                "recommendations": result.get("recommendations", []),
                "result_data": {
                    "score_items": result.get("score_items", []),
                    "trust_stack_assessment": result.get("trust_stack_assessment", {}),
                    "sentiment_themes": result.get("sentiment_themes", {}),
                    "strengths": result.get("strengths", []),
                    "weaknesses": result.get("weaknesses", []),
                    "recommendations": result.get("recommendations", []),
                },
            }
        except Exception as e:
            logger.error(f"Review sentiment analysis failed: {e}")
            return self._fallback_result()

    def _extract_testimonials(self) -> str:
        all_testimonials = []
        for page in self.context.pages.values():
            all_testimonials.extend(page.testimonials)
        if not all_testimonials:
            return "No testimonials found on the website."
        return "\n".join(f"- {t[:300]}" for t in all_testimonials[:15])

    def _extract_proof_elements(self) -> str:
        lines = []
        for page in self.context.pages.values():
            for cta in page.ctas:
                text = cta.get("text", "").lower()
                if any(kw in text for kw in ["customer", "case stud", "success"]):
                    lines.append(f"- CTA: {cta.get('text', '')}")
        # Count testimonial-bearing pages
        testimonial_pages = sum(
            1 for p in self.context.pages.values() if p.testimonials
        )
        lines.append(f"- Pages with testimonials: {testimonial_pages}")
        return "\n".join(lines) or "Limited proof elements found."

    async def _get_mock_review_data(self) -> dict:
        try:
            from agents.data_providers.mock_g2 import MockG2Provider
            provider = MockG2Provider()
            return await provider.get_data(self.context.company_url)
        except ImportError:
            return {"_source": "unavailable", "note": "Mock G2 provider not implemented yet"}

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
            "analysis_text": "Review analysis incomplete — limited data available.",
            "recommendations": [],
            "result_data": {"fallback": True, "strengths": [], "weaknesses": []},
        }

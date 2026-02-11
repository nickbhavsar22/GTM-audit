"""Review & Sentiment Agent — analyzes G2/Capterra reviews and customer sentiment."""

import json
import logging
from typing import Any

from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

REVIEW_SYSTEM = """You are a customer sentiment analyst specializing in B2B SaaS.
Analyze the available data to assess customer perception, review sentiment, and brand reputation.
If review data is limited, focus on testimonials and social proof from the website."""

REVIEW_PROMPT = """Analyze customer sentiment and review data for this B2B SaaS company.

Website: {company_url}
Company Name: {company_name}

TESTIMONIALS FROM WEBSITE:
{testimonials}

PROOF ELEMENTS (logos, metrics, awards):
{proof_elements}

MOCK REVIEW DATA (G2/Capterra estimates):
{review_data}

Provide a JSON response:
{{
    "overall_score": <number 0-100>,
    "score_items": [
        {{"name": "Testimonial Quality & Quantity", "score": <0-100>, "max_score": 100, "weight": 1.5, "notes": "..."}},
        {{"name": "Social Proof Display", "score": <0-100>, "max_score": 100, "weight": 1.3, "notes": "..."}},
        {{"name": "Customer Logo Showcase", "score": <0-100>, "max_score": 100, "weight": 1.0, "notes": "..."}},
        {{"name": "Case Study Presence", "score": <0-100>, "max_score": 100, "weight": 1.2, "notes": "..."}},
        {{"name": "Review Platform Presence", "score": <0-100>, "max_score": 100, "weight": 1.0, "notes": "..."}},
        {{"name": "Trust Signal Effectiveness", "score": <0-100>, "max_score": 100, "weight": 1.0, "notes": "..."}}
    ],
    "sentiment_themes": {{
        "positive": ["list of positive themes"],
        "negative": ["list of negative themes or gaps"]
    }},
    "strengths": ["3-5 sentiment/review strengths"],
    "weaknesses": ["3-5 sentiment/review weaknesses"],
    "recommendations": [
        {{
            "issue": "review/sentiment issue",
            "recommendation": "what to do",
            "current_state": "current state",
            "best_practice": "best practice",
            "impact": "High|Medium|Low",
            "effort": "High|Medium|Low",
            "implementation_steps": ["step 1", "step 2"],
            "success_metrics": ["metric"],
            "timeline": "timeframe"
        }}
    ],
    "analysis_summary": "2-3 paragraph sentiment analysis"
}}"""


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

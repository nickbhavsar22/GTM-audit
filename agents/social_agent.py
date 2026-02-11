"""Social & Engagement Agent — analyzes social media presence and content strategy."""

import json
import logging
from typing import Any

from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

SOCIAL_SYSTEM = """You are a B2B social media and content strategist.
Analyze the company's social media presence and content strategy based on the available data.
Focus on what can be inferred from the website about their social strategy."""

SOCIAL_PROMPT = """Analyze social media presence and content strategy for this B2B SaaS company.

Website: {company_url}
Company Name: {company_name}

SOCIAL LINKS FOUND ON WEBSITE:
{social_links}

BLOG/CONTENT PAGES FOUND:
{content_pages}

WEBSITE CONTENT THEMES:
{content_themes}

Provide a JSON response:
{{
    "overall_score": <number 0-100>,
    "score_items": [
        {{"name": "Social Platform Presence", "score": <0-100>, "max_score": 100, "weight": 1.2, "notes": "..."}},
        {{"name": "Content Strategy Visibility", "score": <0-100>, "max_score": 100, "weight": 1.5, "notes": "..."}},
        {{"name": "Blog/Resource Quality", "score": <0-100>, "max_score": 100, "weight": 1.3, "notes": "..."}},
        {{"name": "Social Proof Integration", "score": <0-100>, "max_score": 100, "weight": 1.0, "notes": "..."}},
        {{"name": "Content Freshness", "score": <0-100>, "max_score": 100, "weight": 1.0, "notes": "..."}},
        {{"name": "Thought Leadership Signals", "score": <0-100>, "max_score": 100, "weight": 1.0, "notes": "..."}}
    ],
    "platforms_detected": {{"linkedin": "url", "twitter": "url"}},
    "content_assessment": {{
        "has_blog": true/false,
        "blog_page_count": <number>,
        "content_themes": ["themes identified"],
        "content_freshness": "active/stale/unknown"
    }},
    "strengths": ["3-5 social/content strengths"],
    "weaknesses": ["3-5 social/content weaknesses"],
    "recommendations": [
        {{
            "issue": "social/content issue",
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
    "analysis_summary": "2-3 paragraph social/content analysis"
}}"""


class SocialAgent(BaseAgent):
    agent_name = "social"
    agent_display_name = "Social & Engagement"
    dependencies = ["web_scraper"]

    async def run(self) -> dict[str, Any]:
        await self.update_progress(10, "Detecting social media presence")

        social_links = self._extract_social_links()
        content_pages = self._extract_content_pages()
        content_themes = self._extract_content_themes()

        await self.update_progress(40, "Analyzing social presence with AI")

        prompt = SOCIAL_PROMPT.format(
            company_url=self.context.company_url,
            company_name=self.context.company_name or "Unknown",
            social_links=social_links,
            content_pages=content_pages,
            content_themes=content_themes,
        )

        try:
            response = await self.call_llm_json(prompt, system=SOCIAL_SYSTEM)
            result = self.parse_json(response)

            if not result:
                return self._fallback_result()

            await self.update_progress(85, "Compiling social report")

            return {
                "score": result.get("overall_score", 50),
                "grade": None,
                "analysis_text": result.get("analysis_summary", ""),
                "recommendations": result.get("recommendations", []),
                "result_data": {
                    "score_items": result.get("score_items", []),
                    "platforms_detected": result.get("platforms_detected", {}),
                    "content_assessment": result.get("content_assessment", {}),
                    "strengths": result.get("strengths", []),
                    "weaknesses": result.get("weaknesses", []),
                    "recommendations": result.get("recommendations", []),
                },
            }
        except Exception as e:
            logger.error(f"Social analysis failed: {e}")
            return self._fallback_result()

    def _extract_social_links(self) -> str:
        all_social = {}
        for page in self.context.pages.values():
            for platform, url in page.social_links.items():
                if platform not in all_social:
                    all_social[platform] = url
        if not all_social:
            return "No social media links found on the website."
        return "\n".join(f"- {p}: {u}" for p, u in all_social.items())

    def _extract_content_pages(self) -> str:
        blog_pages = self.context.get_pages_by_type("blog")
        resource_pages = self.context.get_pages_by_type("resources")
        pages = blog_pages + resource_pages

        if not pages:
            return "No blog or resource pages found."

        lines = [f"Found {len(pages)} content pages:"]
        for page in pages[:10]:
            lines.append(f"- {page.title} ({page.url})")
        return "\n".join(lines)

    def _extract_content_themes(self) -> str:
        """Extract H2 tags from blog/content pages as theme indicators."""
        themes = []
        for page in self.context.pages.values():
            if page.page_type in ("blog", "resources"):
                themes.extend(page.h2_tags[:3])
        if not themes:
            return "Unable to determine content themes."
        return "\n".join(f"- {t}" for t in themes[:20])

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
            "analysis_text": "Social analysis incomplete — LLM analysis unavailable.",
            "recommendations": [],
            "result_data": {"fallback": True, "strengths": [], "weaknesses": []},
        }

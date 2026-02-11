"""SEO & Visibility Agent — analyzes technical SEO, keywords, page speed, and organic visibility."""

import json
import logging
from typing import Any
from urllib.parse import urlparse

from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

SEO_SYSTEM = """You are an expert technical SEO analyst specializing in B2B SaaS websites.
Analyze the provided website data and produce a comprehensive SEO audit.
Be specific with examples and evidence from the actual content provided."""

SEO_PROMPT = """Analyze this B2B SaaS company's website for SEO effectiveness.

Website: {company_url}
Pages Crawled: {pages_crawled}

WEBSITE DATA:
{site_data}

Provide a JSON response with this structure:
{{
    "overall_score": <number 0-100>,
    "score_items": [
        {{"name": "Title Tag Optimization", "score": <0-100>, "max_score": 100, "weight": 1.5, "notes": "..."}},
        {{"name": "Meta Description Quality", "score": <0-100>, "max_score": 100, "weight": 1.0, "notes": "..."}},
        {{"name": "Header Structure (H1-H3)", "score": <0-100>, "max_score": 100, "weight": 1.2, "notes": "..."}},
        {{"name": "Internal Linking", "score": <0-100>, "max_score": 100, "weight": 1.0, "notes": "..."}},
        {{"name": "Schema Markup", "score": <0-100>, "max_score": 100, "weight": 0.8, "notes": "..."}},
        {{"name": "Page Speed Indicators", "score": <0-100>, "max_score": 100, "weight": 1.0, "notes": "..."}},
        {{"name": "Mobile Optimization", "score": <0-100>, "max_score": 100, "weight": 1.0, "notes": "..."}},
        {{"name": "Content Depth & Quality", "score": <0-100>, "max_score": 100, "weight": 1.3, "notes": "..."}}
    ],
    "strengths": ["list of 3-5 SEO strengths with specific evidence"],
    "weaknesses": ["list of 3-5 SEO weaknesses with specific evidence"],
    "recommendations": [
        {{
            "issue": "specific issue found",
            "recommendation": "what to do about it",
            "current_state": "what it currently looks like",
            "best_practice": "industry standard",
            "impact": "High|Medium|Low",
            "effort": "High|Medium|Low",
            "implementation_steps": ["step 1", "step 2", "step 3"],
            "success_metrics": ["metric 1"],
            "timeline": "1-2 weeks"
        }}
    ],
    "analysis_summary": "2-3 paragraph analysis of the site's SEO performance"
}}

Generate 5-8 specific, actionable recommendations based on actual issues found."""


class SEOAgent(BaseAgent):
    agent_name = "seo"
    agent_display_name = "SEO & Visibility"
    dependencies = ["web_scraper"]

    async def run(self) -> dict[str, Any]:
        """Analyze the website's SEO performance."""
        await self.update_progress(10, "Extracting SEO data from pages")

        # Build SEO-focused data from scraped pages
        site_data = self._extract_seo_data()

        await self.update_progress(30, "Running technical SEO analysis")

        # Get mock SEMrush data if available
        mock_data = await self._get_mock_seo_data()
        if mock_data:
            site_data += f"\n\nSEO METRICS (estimated):\n{json.dumps(mock_data, indent=2)}"

        await self.update_progress(50, "Analyzing with AI")

        prompt = SEO_PROMPT.format(
            company_url=self.context.company_url,
            pages_crawled=len(self.context.pages),
            site_data=site_data,
        )

        try:
            response = await self.call_llm_json(prompt, system=SEO_SYSTEM)
            result = self.parse_json(response)

            if not result:
                return self._fallback_analysis()

            await self.update_progress(85, "Compiling SEO report")

            return {
                "score": result.get("overall_score", 50),
                "grade": None,  # Computed from ModuleScore
                "analysis_text": result.get("analysis_summary", ""),
                "recommendations": result.get("recommendations", []),
                "result_data": {
                    "score_items": result.get("score_items", []),
                    "strengths": result.get("strengths", []),
                    "weaknesses": result.get("weaknesses", []),
                    "recommendations": result.get("recommendations", []),
                },
            }
        except Exception as e:
            logger.error(f"SEO analysis failed: {e}")
            return self._fallback_analysis()

    def _extract_seo_data(self) -> str:
        """Extract SEO-relevant data from all scraped pages."""
        lines = []
        for url, page in self.context.pages.items():
            lines.append(f"\n--- PAGE: {url} ---")
            lines.append(f"Title: {page.title}")
            lines.append(f"Meta Description: {page.meta_description}")
            lines.append(f"H1 Tags: {', '.join(page.h1_tags) or 'NONE'}")
            lines.append(f"H2 Tags: {', '.join(page.h2_tags[:5]) or 'NONE'}")
            lines.append(f"H3 Tags: {', '.join(page.h3_tags[:3]) or 'NONE'}")
            lines.append(f"Load Time: {page.load_time:.2f}s")
            lines.append(f"Internal Links: {len(page.internal_links)}")
            lines.append(f"External Links: {len(page.external_links)}")
            lines.append(f"Images: {len(page.images)}")
            lines.append(f"Has Schema: {page.has_schema}")
            if page.schema_types:
                lines.append(f"Schema Types: {', '.join(page.schema_types)}")
            lines.append(f"Page Type: {page.page_type}")
            # Check for alt text on images
            images_without_alt = sum(
                1 for img in page.images if not img.get("alt")
            )
            lines.append(f"Images Without Alt Text: {images_without_alt}/{len(page.images)}")

        return "\n".join(lines)[:25000]  # Limit for LLM context

    async def _get_mock_seo_data(self) -> dict | None:
        """Get mock SEMrush-style data."""
        try:
            from agents.data_providers.mock_semrush import MockSEMrushProvider
            provider = MockSEMrushProvider()
            return await provider.get_data(self.context.company_url)
        except ImportError:
            return None

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

    def _fallback_analysis(self) -> dict[str, Any]:
        """Generate a basic SEO score from raw data when LLM fails."""
        score_items = []
        pages = list(self.context.pages.values())

        # Title analysis
        pages_with_titles = sum(1 for p in pages if p.title)
        title_score = (pages_with_titles / max(len(pages), 1)) * 100
        score_items.append({
            "name": "Title Tag Optimization",
            "score": title_score,
            "max_score": 100,
            "weight": 1.5,
            "notes": f"{pages_with_titles}/{len(pages)} pages have titles",
        })

        # Meta description analysis
        pages_with_meta = sum(1 for p in pages if p.meta_description)
        meta_score = (pages_with_meta / max(len(pages), 1)) * 100
        score_items.append({
            "name": "Meta Description Quality",
            "score": meta_score,
            "max_score": 100,
            "weight": 1.0,
            "notes": f"{pages_with_meta}/{len(pages)} pages have meta descriptions",
        })

        # H1 analysis
        pages_with_h1 = sum(1 for p in pages if p.h1_tags)
        h1_score = (pages_with_h1 / max(len(pages), 1)) * 100
        score_items.append({
            "name": "Header Structure (H1-H3)",
            "score": h1_score,
            "max_score": 100,
            "weight": 1.2,
            "notes": f"{pages_with_h1}/{len(pages)} pages have H1 tags",
        })

        avg_score = sum(i["score"] for i in score_items) / max(len(score_items), 1)

        return {
            "score": avg_score,
            "grade": None,
            "analysis_text": "Basic SEO analysis from raw page data (LLM analysis unavailable).",
            "recommendations": [],
            "result_data": {
                "score_items": score_items,
                "strengths": [],
                "weaknesses": [],
                "fallback": True,
            },
        }

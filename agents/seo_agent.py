"""SEO & Visibility Agent — analyzes technical SEO, keywords, page speed, and organic visibility."""

import json
import logging
from typing import Any
from urllib.parse import urlparse

from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

SEO_SYSTEM = """You are a senior SEO strategist who has audited 200+ B2B SaaS websites. You go beyond technical checklist items to explain the business impact of every finding — how each issue affects organic traffic, lead generation, and pipeline. You cite specific pages and tags from the actual content and compare to industry best practices with named examples. Your analysis reads like a $5K SEO audit from a top agency, not a Screaming Frog export.

You are a senior B2B marketing consultant. Write findings in terms of pipeline, revenue, and buyer behavior — not technical implementation details. Be specific to this company. Avoid generic consulting language like 'leverage' and 'optimize.' Conservative and transparent beats optimistic and unsupported. Show your calculation for any projected outcome."""

SEO_PROMPT = """Perform a comprehensive SEO and organic visibility audit for this B2B SaaS company's website.

Website: {company_url}
Pages Crawled: {pages_crawled}

WEBSITE DATA:
{site_data}

CRITICAL INSTRUCTIONS:
- For every finding, explain the BUSINESS IMPACT — not just what's wrong, but what it's likely costing in organic traffic and leads. Use directional estimates (e.g., "missing meta descriptions on 6/10 pages likely reduces CTR by 20-30% on those pages").
- Quote SPECIFIC page titles, meta descriptions, and H1 tags from the actual content.
- Compare findings to INDUSTRY BEST PRACTICES with named examples of B2B SaaS companies doing it well.
- For each recommendation, include BEFORE/AFTER examples showing what the fix looks like.
- Write analysis_summary as a strategic narrative for a CMO, not a list of technical findings.

Provide a JSON response with this structure:
{{
    "overall_score": <number 0-100>,
    "score_items": [
        {{"name": "Title Tag Optimization", "score": <0-100>, "max_score": 100, "weight": 1.5, "notes": "Quote actual title tags and assess keyword targeting"}},
        {{"name": "Meta Description Quality", "score": <0-100>, "max_score": 100, "weight": 1.0, "notes": "Quote actual meta descriptions and assess click appeal"}},
        {{"name": "Header Structure (H1-H3)", "score": <0-100>, "max_score": 100, "weight": 1.2, "notes": "Assess content hierarchy and keyword integration"}},
        {{"name": "Internal Linking", "score": <0-100>, "max_score": 100, "weight": 1.0, "notes": "Assess link equity distribution and navigation structure"}},
        {{"name": "Schema Markup", "score": <0-100>, "max_score": 100, "weight": 0.8, "notes": "Assess structured data implementation for rich results"}},
        {{"name": "Page Speed Indicators", "score": <0-100>, "max_score": 100, "weight": 1.0, "notes": "Assess load time impact on rankings and UX"}},
        {{"name": "Mobile Optimization", "score": <0-100>, "max_score": 100, "weight": 1.0, "notes": "Assess mobile-first indexing readiness"}},
        {{"name": "Content Depth & Quality", "score": <0-100>, "max_score": 100, "weight": 1.3, "notes": "Assess content comprehensiveness for target keywords"}}
    ],
    "strengths": ["3-5 SEO strengths with specific evidence and quoted content"],
    "weaknesses": ["3-5 SEO weaknesses with business impact estimates"],
    "recommendations": [
        {{
            "issue": "specific issue found with quoted evidence",
            "recommendation": "what to do about it",
            "business_impact": "estimated effect on organic traffic/rankings (e.g., 'likely suppressing organic CTR by 15-25%')",
            "before_example": "current title/meta/content quoted from the site",
            "after_example": "suggested replacement with rationale",
            "current_state": "description of current state",
            "best_practice": "named example of a B2B SaaS company doing this well",
            "impact": "High|Medium|Low",
            "effort": "High|Medium|Low",
            "implementation_steps": ["step 1", "step 2", "step 3"],
            "success_metrics": ["metric to track improvement"],
            "timeline": "timeframe"
        }}
    ],
    "analysis_summary": "3-4 paragraph strategic narrative about the site's SEO performance, written for a CMO. Frame the core SEO problem, explain what it's costing in organic visibility, and outline what an optimized SEO strategy would accomplish."
}}

Generate 5-8 specific, actionable recommendations with quoted before/after examples from the actual content."""


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

        await self.update_progress(45, "Building SEO analysis prompt")

        prompt = SEO_PROMPT.format(
            company_url=self.context.company_url,
            pages_crawled=len(self.context.pages),
            site_data=site_data,
        )

        await self.update_progress(50, "Sending to AI for SEO analysis")

        try:
            response = await self.call_llm_json(prompt, system=SEO_SYSTEM)

            await self.update_progress(75, "Parsing AI response")
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

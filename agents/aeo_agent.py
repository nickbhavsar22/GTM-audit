"""Answer Engine Optimization Agent — analyzes AEO readiness for AI-powered search engines.

Checks schema markup, content structure, citation readiness, and answer-focused content
based on best practices for appearing in AI Overviews, ChatGPT, Perplexity, and similar
answer engines.
"""

import json
import logging
import re
from typing import Any

from agents.base_agent import ANTI_HALLUCINATION_INSTRUCTION, BaseAgent

logger = logging.getLogger(__name__)

# Question word patterns for heading analysis
QUESTION_WORDS = re.compile(
    r"^\s*(who|what|when|where|why|how|can|does|is|are|do|should|will|which|could)\b",
    re.IGNORECASE,
)

# Table of contents patterns in HTML
TOC_PATTERNS = [
    re.compile(r'id\s*=\s*["\'](?:toc|table-of-contents|tableofcontents)["\']', re.IGNORECASE),
    re.compile(r'class\s*=\s*["\'][^"\']*(?:toc|table-of-contents|tableofcontents)[^"\']*["\']', re.IGNORECASE),
    re.compile(r'<nav[^>]*>.*?<(?:ul|ol)[^>]*>(?:.*?<a[^>]+href\s*=\s*["\']#[^"\']+["\'].*?){3,}', re.IGNORECASE | re.DOTALL),
]

# FAQ detection patterns
FAQ_PATTERNS = [
    re.compile(r'<script[^>]*type\s*=\s*["\']application/ld\+json["\'][^>]*>.*?"@type"\s*:\s*"FAQPage"', re.IGNORECASE | re.DOTALL),
    re.compile(r"<details[^>]*>.*?<summary", re.IGNORECASE | re.DOTALL),
    re.compile(r'itemtype\s*=\s*["\'].*?FAQPage', re.IGNORECASE),
]

AEO_SYSTEM = """You are a senior Answer Engine Optimization (AEO) strategist who specializes in optimizing B2B websites for AI-powered search engines — ChatGPT, Perplexity, Google AI Overviews, and similar answer engines. You understand the shift from traditional keyword-based SEO to answer-focused content that AI engines cite and surface.

Key principles you apply:
- Content should answer questions directly, not just target keywords
- JSON-LD schema markup dramatically increases citation rates (42% increase with structured data)
- Brand mentions in third-party sources correlate most strongly with AI overview appearances (0.664 correlation)
- Table of contents in blog posts increases AI-sourced traffic by 59%
- 95% of mid-funnel search sources are third-party websites

You are a senior B2B marketing consultant. Write findings in terms of pipeline, revenue, and buyer behavior — not technical implementation details. Be specific to this company. Avoid generic consulting language like 'leverage' and 'optimize.' Conservative and transparent beats optimistic and unsupported.""" + ANTI_HALLUCINATION_INSTRUCTION

AEO_PROMPT = """Perform a comprehensive Answer Engine Optimization (AEO) audit for this company's website. AEO is the practice of optimizing content so AI-powered answer engines (ChatGPT, Perplexity, Google AI Overviews) cite and surface your brand.

Website: {company_url}
Pages Crawled: {pages_crawled}

AUTOMATED CHECK RESULTS (deterministic analysis already completed):
{automated_checks}

WEBSITE DATA:
{site_data}

CRITICAL INSTRUCTIONS:
- For every finding, explain the BUSINESS IMPACT — what it's costing in AI search visibility and citations.
- Reference the automated check results above and provide strategic context for each finding.
- Quote SPECIFIC content from the site (headings, meta descriptions, content snippets).
- Compare to companies in this industry or similar industries that excel at AEO.
- For each recommendation, provide BEFORE/AFTER examples using actual content from the site.
- Frame recommendations around the "5% that moves the needle": new question-based pages, content enhancements, and citation optimization.

Provide a JSON response with this structure:
{{
    "overall_score": <number 0-100>,
    "score_items": [
        {{"name": "JSON-LD Schema Markup", "score": <0-100>, "max_score": 100, "weight": 1.8, "notes": "Assess structured data implementation — JSON-LD presence, schema types, completeness. 73% of first-page results use schema, 42% citation increase with structured data."}},
        {{"name": "Answer-Focused Content Structure", "score": <0-100>, "max_score": 100, "weight": 1.5, "notes": "Assess whether content directly answers buyer questions vs. keyword-stuffed. Look for question-format headings, direct answer paragraphs, clear definitions."}},
        {{"name": "Citation Readiness", "score": <0-100>, "max_score": 100, "weight": 1.5, "notes": "How well-structured is the content for AI engines to cite? Clear claims, attributed data, authoritative tone, concise answers."}},
        {{"name": "Table of Contents", "score": <0-100>, "max_score": 100, "weight": 1.2, "notes": "Blog posts with ToC see 59% more AI-sourced traffic. Check presence on content pages."}},
        {{"name": "Content Gap Coverage", "score": <0-100>, "max_score": 100, "weight": 1.2, "notes": "What buyer questions are left unanswered? Identify topics where new question-based pages should be created."}},
        {{"name": "Meta Description AI-Readiness", "score": <0-100>, "max_score": 100, "weight": 1.0, "notes": "Are meta descriptions written as concise answers that AI engines can extract?"}},
        {{"name": "Brand Authority Signals", "score": <0-100>, "max_score": 100, "weight": 1.0, "notes": "Brand mentions > backlinks for AI visibility. Assess brand positioning strength, unique claims, thought leadership signals."}},
        {{"name": "Image Alt Text Quality", "score": <0-100>, "max_score": 100, "weight": 0.8, "notes": "Descriptive alt text helps AI engines understand visual content. Assess coverage and quality."}}
    ],
    "strengths": ["3-5 AEO strengths with specific evidence from the site"],
    "weaknesses": ["3-5 AEO weaknesses with business impact estimates — frame as lost AI visibility"],
    "citation_readiness": {{
        "score": <0-100>,
        "analysis": "2-3 paragraph assessment of how citable the site's content is for AI engines",
        "top_opportunities": ["3-5 specific content pieces that could be optimized for citation"]
    }},
    "content_gaps": [
        {{
            "question": "A specific buyer question the site doesn't answer",
            "suggested_page_title": "Proposed page title targeting this question",
            "suggested_url_slug": "/blog/proposed-url-slug",
            "priority": "High|Medium|Low",
            "estimated_impact": "Why this page would capture AI search traffic",
            "content_outline": "3-5 bullet points for what this page should cover"
        }}
    ],
    "brand_authority_assessment": "2-3 paragraph analysis of the brand's potential for third-party mentions and AI citations. Consider: unique data/research, thought leadership content, product differentiation, industry positioning.",
    "recommendations": [
        {{
            "issue": "specific issue found with quoted evidence from the site",
            "recommendation": "what to do about it — specific and actionable",
            "business_impact": "estimated effect on AI search visibility (e.g., 'implementing FAQ schema could increase AI citations by 30-40%')",
            "before_example": "current content/markup quoted from the site",
            "after_example": "suggested AEO-optimized version",
            "current_state": "description of current state",
            "best_practice": "named example of a company doing this well",
            "impact": "High|Medium|Low",
            "effort": "High|Medium|Low",
            "implementation_steps": ["step 1", "step 2", "step 3"],
            "success_metrics": ["metric to track improvement"],
            "timeline": "timeframe",
            "owner": "Marketing|Engineering|Content"
        }}
    ],
    "analysis_summary": "3-4 paragraph strategic narrative about the site's AEO readiness, written for a CMO. Frame the shift from traditional SEO to AEO, explain what the company is leaving on the table by not optimizing for AI engines, and outline what a strong AEO strategy would accomplish in 90 days."
}}

Generate 5-8 specific, actionable recommendations with before/after examples. Prioritize the three things that move the needle most: new question-based pages, content enhancements for existing pages, and citation optimization."""


class AEOAgent(BaseAgent):
    agent_name = "aeo"
    agent_display_name = "Answer Engine Optimization"
    dependencies = ["web_scraper"]

    async def run(self) -> dict[str, Any]:
        """Analyze the website's AEO readiness for AI-powered search engines."""
        await self.update_progress(10, "Extracting AEO data from pages")

        if not self.has_sufficient_data():
            return self._insufficient_data_result("No website content available for AEO analysis.")

        # Run deterministic checks first
        automated_checks = self._run_automated_checks()

        await self.update_progress(30, "Automated AEO checks complete")

        # Build site data for LLM analysis
        site_data = self._extract_aeo_data()

        await self.update_progress(45, "Building AEO analysis prompt")

        prompt = AEO_PROMPT.format(
            company_url=self.context.company_url,
            pages_crawled=len(self.context.pages),
            automated_checks=json.dumps(automated_checks, indent=2),
            site_data=site_data,
        )

        await self.update_progress(50, "Sending to AI for AEO analysis")

        try:
            response = await self.call_llm_json(prompt, system=AEO_SYSTEM)

            await self.update_progress(75, "Parsing AI response")
            result = self.parse_json(response)

            if not result:
                return self._fallback_analysis(automated_checks)

            await self.update_progress(85, "Compiling AEO report")

            return {
                "score": result.get("overall_score", 50),
                "grade": None,
                "analysis_text": result.get("analysis_summary", ""),
                "recommendations": result.get("recommendations", []),
                "result_data": {
                    "score_items": result.get("score_items", []),
                    "strengths": result.get("strengths", []),
                    "weaknesses": result.get("weaknesses", []),
                    "recommendations": result.get("recommendations", []),
                    "automated_checks": automated_checks,
                    "citation_readiness": result.get("citation_readiness", {}),
                    "content_gaps": result.get("content_gaps", []),
                    "brand_authority_assessment": result.get(
                        "brand_authority_assessment", ""
                    ),
                },
            }
        except Exception as e:
            logger.error(f"AEO analysis failed: {e}")
            return self._fallback_analysis(automated_checks)

    # -------------------------------------------------------------------------
    # Deterministic checks
    # -------------------------------------------------------------------------

    def _run_automated_checks(self) -> dict[str, Any]:
        """Run all deterministic AEO checks against crawled pages."""
        pages = list(self.context.pages.values())
        return {
            "schema_markup": self._check_schema_markup(pages),
            "table_of_contents": self._check_table_of_contents(pages),
            "alt_text": self._check_alt_text(pages),
            "question_headings": self._check_question_headings(pages),
            "faq_sections": self._check_faq_sections(pages),
            "meta_descriptions": self._check_meta_descriptions(pages),
        }

    def _check_schema_markup(self, pages: list) -> dict[str, Any]:
        """Check JSON-LD structured data presence and types."""
        total = len(pages)
        pages_with_schema = 0
        pages_with_json_ld = 0
        all_schema_types: list[str] = []
        json_ld_details: list[dict] = []

        recommended_types = {"FAQPage", "HowTo", "Article", "Organization",
                             "Product", "WebPage", "BreadcrumbList"}

        for page in pages:
            if page.has_schema:
                pages_with_schema += 1

            # Parse HTML for JSON-LD blocks
            json_ld_blocks = re.findall(
                r'<script[^>]*type\s*=\s*["\']application/ld\+json["\'][^>]*>(.*?)</script>',
                page.html or "",
                re.IGNORECASE | re.DOTALL,
            )

            if json_ld_blocks:
                pages_with_json_ld += 1
                for block in json_ld_blocks:
                    try:
                        data = json.loads(block.strip())
                        schema_type = data.get("@type", "Unknown")
                        if isinstance(schema_type, list):
                            all_schema_types.extend(schema_type)
                        else:
                            all_schema_types.append(schema_type)
                        json_ld_details.append({
                            "url": page.url,
                            "type": schema_type,
                            "has_name": bool(data.get("name")),
                            "has_description": bool(data.get("description")),
                        })
                    except (json.JSONDecodeError, AttributeError):
                        all_schema_types.append("Invalid JSON-LD")

            # Also include schema types from the web scraper
            if page.schema_types:
                all_schema_types.extend(page.schema_types)

        unique_types = set(all_schema_types)
        missing_recommended = recommended_types - unique_types

        return {
            "pages_with_schema": pages_with_schema,
            "pages_with_json_ld": pages_with_json_ld,
            "total_pages": total,
            "schema_types_found": sorted(unique_types),
            "missing_recommended_types": sorted(missing_recommended),
            "json_ld_details": json_ld_details,
            "pass": pages_with_json_ld > 0,
        }

    def _check_table_of_contents(self, pages: list) -> dict[str, Any]:
        """Check for table of contents in blog/content pages."""
        blog_pages = [
            p for p in pages
            if p.page_type in ("blog", "blog_post", "article")
            or p.content_type in ("blog_post", "article", "guide")
            or "/blog/" in (p.url or "")
            or "/posts/" in (p.url or "")
            or "/articles/" in (p.url or "")
        ]

        pages_with_toc = 0
        toc_details: list[dict] = []

        for page in blog_pages:
            html = page.html or ""
            has_toc = any(pattern.search(html) for pattern in TOC_PATTERNS)

            # Additional check: look for lists of anchor links near the top
            if not has_toc:
                # Find anchor link clusters (3+ links to #sections)
                anchor_links = re.findall(r'<a[^>]+href\s*=\s*["\']#[^"\']+["\']', html[:5000])
                if len(anchor_links) >= 3:
                    has_toc = True

            if has_toc:
                pages_with_toc += 1

            toc_details.append({
                "url": page.url,
                "has_toc": has_toc,
                "page_type": page.page_type,
            })

        total_blog = len(blog_pages)
        return {
            "blog_pages_with_toc": pages_with_toc,
            "total_blog_pages": total_blog,
            "percentage": (pages_with_toc / max(total_blog, 1)) * 100,
            "details": toc_details,
            "pass": total_blog == 0 or (pages_with_toc / max(total_blog, 1)) >= 0.5,
        }

    def _check_alt_text(self, pages: list) -> dict[str, Any]:
        """Check image alt text coverage and quality."""
        total_images = 0
        images_with_alt = 0
        images_with_descriptive_alt = 0

        for page in pages:
            for img in page.images:
                total_images += 1
                alt = img.get("alt", "").strip()
                if alt:
                    images_with_alt += 1
                    # Consider "descriptive" if alt text is > 5 chars and not
                    # just a filename pattern (e.g., "img_001.png")
                    if len(alt) > 5 and not re.match(r"^[\w\-]+\.\w{3,4}$", alt):
                        images_with_descriptive_alt += 1

        coverage = (images_with_alt / max(total_images, 1)) * 100
        return {
            "images_with_alt": images_with_alt,
            "images_with_descriptive_alt": images_with_descriptive_alt,
            "total_images": total_images,
            "coverage_percentage": round(coverage, 1),
            "pass": coverage >= 80,
        }

    def _check_question_headings(self, pages: list) -> dict[str, Any]:
        """Check how many headings are phrased as questions."""
        total_headings = 0
        question_headings = 0
        question_examples: list[str] = []

        for page in pages:
            for heading in page.h2_tags + page.h3_tags:
                total_headings += 1
                if QUESTION_WORDS.match(heading) or heading.strip().endswith("?"):
                    question_headings += 1
                    if len(question_examples) < 5:
                        question_examples.append(heading)

        percentage = (question_headings / max(total_headings, 1)) * 100
        return {
            "question_headings_count": question_headings,
            "total_headings": total_headings,
            "percentage": round(percentage, 1),
            "examples": question_examples,
            "pass": percentage >= 20,
        }

    def _check_faq_sections(self, pages: list) -> dict[str, Any]:
        """Check for FAQ sections and FAQ schema."""
        pages_with_faq = 0
        has_faq_schema = False
        faq_details: list[dict] = []

        for page in pages:
            html = page.html or ""
            found_faq = False

            # Check FAQ patterns in HTML
            for pattern in FAQ_PATTERNS:
                if pattern.search(html):
                    found_faq = True
                    if "FAQPage" in pattern.pattern:
                        has_faq_schema = True
                    break

            # Check headings for FAQ mentions
            if not found_faq:
                all_headings = page.h1_tags + page.h2_tags + page.h3_tags
                for heading in all_headings:
                    if re.search(r"\bfaq\b|frequently\s+asked|common\s+questions", heading, re.IGNORECASE):
                        found_faq = True
                        break

            if found_faq:
                pages_with_faq += 1
                faq_details.append({"url": page.url, "has_faq_schema": has_faq_schema})

        return {
            "pages_with_faq": pages_with_faq,
            "has_faq_schema": has_faq_schema,
            "details": faq_details,
            "pass": pages_with_faq > 0,
        }

    def _check_meta_descriptions(self, pages: list) -> dict[str, Any]:
        """Check meta description presence and AI-readiness."""
        total = len(pages)
        pages_with_meta = 0
        good_length = 0  # 120-160 chars is ideal for AI extraction

        for page in pages:
            meta = (page.meta_description or "").strip()
            if meta:
                pages_with_meta += 1
                if 120 <= len(meta) <= 160:
                    good_length += 1

        coverage = (pages_with_meta / max(total, 1)) * 100
        return {
            "pages_with_meta": pages_with_meta,
            "pages_with_good_length": good_length,
            "total_pages": total,
            "coverage_percentage": round(coverage, 1),
            "pass": coverage >= 80,
        }

    # -------------------------------------------------------------------------
    # Data extraction for LLM
    # -------------------------------------------------------------------------

    def _extract_aeo_data(self) -> str:
        """Extract AEO-relevant data from all scraped pages."""
        lines = []
        for url, page in self.context.pages.items():
            quality = page.extraction_quality()
            lines.append(f"\n--- PAGE: {url} ---")
            if quality == "LOW":
                lines.append("[NOTE: Extraction confidence is LOW for this page. Missing fields may reflect extraction limitations, not actual site issues.]")
            lines.append(f"Title: {page.title}")
            lines.append(f"Meta Description: {page.meta_description}")
            lines.append(f"Page Type: {page.page_type}")
            lines.append(f"Content Type: {page.content_type}")
            lines.append(f"Word Count: {page.word_count}")
            lines.append(f"H1: {', '.join(page.h1_tags) if page.h1_tags else '[Not extracted — do NOT assume missing from page]'}")
            lines.append(f"H2: {', '.join(page.h2_tags[:8]) if page.h2_tags else '[Not extracted — do NOT assume missing from page]'}")
            lines.append(f"H3: {', '.join(page.h3_tags[:5]) if page.h3_tags else '[Not extracted — do NOT assume missing from page]'}")
            lines.append(f"Has Schema: {page.has_schema}")
            if page.schema_types:
                lines.append(f"Schema Types: {', '.join(page.schema_types)}")
            lines.append(f"Images: {len(page.images)} total, "
                         f"{sum(1 for i in page.images if i.get('alt'))} with alt text")
            # Include content snippet for answer-quality assessment
            content = (page.raw_text or "")[:1500]
            if content:
                lines.append(f"Content Preview: {content}")

        return "\n".join(lines)[:20000]

    # -------------------------------------------------------------------------
    # Fallback
    # -------------------------------------------------------------------------

    def _fallback_analysis(self, automated_checks: dict | None = None) -> dict[str, Any]:
        """Generate AEO score from deterministic checks when LLM fails."""
        if automated_checks is None:
            automated_checks = self._run_automated_checks()

        score_items = []

        # Schema markup (25 points max)
        schema = automated_checks["schema_markup"]
        schema_score = 0
        if schema["pages_with_json_ld"] > 0:
            schema_score = min(100, (schema["pages_with_json_ld"] / max(schema["total_pages"], 1)) * 100)
            # Bonus for having recommended types
            if len(schema["missing_recommended_types"]) <= 3:
                schema_score = min(100, schema_score + 20)
        score_items.append({
            "name": "JSON-LD Schema Markup",
            "score": schema_score,
            "max_score": 100,
            "weight": 1.8,
            "notes": f"{schema['pages_with_json_ld']}/{schema['total_pages']} pages have JSON-LD. "
                     f"Types found: {', '.join(schema['schema_types_found']) or 'none'}",
        })

        # Table of contents (15 points max)
        toc = automated_checks["table_of_contents"]
        toc_score = (toc["blog_pages_with_toc"] / max(toc["total_blog_pages"], 1)) * 100
        score_items.append({
            "name": "Table of Contents",
            "score": toc_score,
            "max_score": 100,
            "weight": 1.2,
            "notes": f"{toc['blog_pages_with_toc']}/{toc['total_blog_pages']} blog pages have ToC",
        })

        # Alt text (10 points max)
        alt = automated_checks["alt_text"]
        score_items.append({
            "name": "Image Alt Text Quality",
            "score": alt["coverage_percentage"],
            "max_score": 100,
            "weight": 0.8,
            "notes": f"{alt['images_with_alt']}/{alt['total_images']} images have alt text",
        })

        # Question headings (15 points max)
        qh = automated_checks["question_headings"]
        # Scale: 0% questions = 0, 20%+ = 100
        qh_score = min(100, qh["percentage"] * 5)
        score_items.append({
            "name": "Answer-Focused Content Structure",
            "score": qh_score,
            "max_score": 100,
            "weight": 1.5,
            "notes": f"{qh['question_headings_count']}/{qh['total_headings']} headings are questions",
        })

        # FAQ sections (15 points max)
        faq = automated_checks["faq_sections"]
        faq_score = 100 if faq["pages_with_faq"] > 0 else 0
        if faq["has_faq_schema"]:
            faq_score = 100
        score_items.append({
            "name": "Content Gap Coverage",
            "score": faq_score,
            "max_score": 100,
            "weight": 1.2,
            "notes": f"{faq['pages_with_faq']} pages with FAQ sections, "
                     f"FAQ schema: {'yes' if faq['has_faq_schema'] else 'no'}",
        })

        # Meta descriptions (20 points max)
        meta = automated_checks["meta_descriptions"]
        score_items.append({
            "name": "Meta Description AI-Readiness",
            "score": meta["coverage_percentage"],
            "max_score": 100,
            "weight": 1.0,
            "notes": f"{meta['pages_with_meta']}/{meta['total_pages']} pages have meta descriptions",
        })

        # Compute weighted average
        total_weight = sum(item["weight"] for item in score_items)
        weighted_sum = sum(item["score"] * item["weight"] for item in score_items)
        avg_score = weighted_sum / max(total_weight, 1)

        return {
            "score": round(avg_score, 1),
            "grade": None,
            "analysis_text": (
                "AEO readiness analysis based on automated checks (LLM analysis unavailable). "
                "The site was evaluated for JSON-LD schema markup, table of contents presence, "
                "image alt text coverage, question-based content structure, FAQ sections, "
                "and meta description quality."
            ),
            "recommendations": [],
            "result_data": {
                "score_items": score_items,
                "strengths": [],
                "weaknesses": [],
                "automated_checks": automated_checks,
                "citation_readiness": {},
                "content_gaps": [],
                "brand_authority_assessment": "",
                "fallback": True,
            },
        }

"""Conversion Optimization Agent — analyzes CRO, forms, CTAs, trust signals, and funnel."""

import json
import logging
from typing import Any

from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

CRO_SYSTEM = """You are a senior B2B SaaS conversion strategist who has optimized funnels for 100+ SaaS companies. You think like a revenue operations leader — every page is either moving buyers toward a decision or losing them. You map the actual buyer journey, identify exactly where pipeline leaks occur, and provide specific fixes with estimated revenue impact. Your analysis reads like a conversion audit from a $10K consultant, not a CRO checklist.

You are a senior B2B marketing consultant. Write findings in terms of pipeline, revenue, and buyer behavior — not technical implementation details. Be specific to this company. Avoid generic consulting language like 'leverage' and 'optimize.' Conservative and transparent beats optimistic and unsupported. Show your calculation for any projected outcome."""

CRO_PROMPT = """Perform a comprehensive conversion and buyer journey audit for this B2B SaaS website. This is a critical section of a premium GTM audit report.

Website: {company_url}

SITE STRUCTURE:
{site_structure}

ALL CTAs FOUND:
{ctas}

ALL FORMS FOUND:
{forms}

KEY PAGES:
{key_pages}

YOUR ANALYSIS MUST INCLUDE:

1. **Buyer Journey Mapping**: Trace the actual path a visitor takes from homepage to conversion. How many clicks from homepage to demo request? What are the available paths? Where do visitors likely drop off?

2. **Demo/Contact Page Teardown**: Analyze the primary conversion page in detail:
   - How many form fields? (Best practice: 3-5 for demos)
   - Is there social proof adjacent to the form?
   - Does the CTA communicate value or just action? ("Get a Demo" vs "See How We Cut Risk by 60%")
   - Are there trust signals (security badges, testimonials, client logos) visible near the form?

3. **CTA Hierarchy Analysis**: Evaluate the CTA ecosystem across the entire site:
   - Is there a clear primary CTA vs. secondary CTAs?
   - Do CTAs change appropriately based on page context?
   - Are there too many competing CTAs creating decision paralysis?

4. **Nurture Path Assessment**: For visitors not ready to buy:
   - Is there a newsletter, content library, or free resource?
   - Are there mid-funnel offers (ROI calculator, assessment, checklist)?
   - Can visitors self-educate without talking to sales?

5. **Trust & Credibility Architecture**: Evaluate the site's trust stack:
   - Where are testimonials, logos, and case studies placed relative to conversion points?
   - Is proof specific (named clients, metrics) or vague (unnamed logos, generic claims)?
   - Are there third-party trust signals (G2 badges, SOC 2, awards)?

6. **Friction Point Identification**: Map specific friction points:
   - Dead-end pages with no CTA
   - Confusing navigation that obscures the conversion path
   - Missing pages that buyers expect (pricing, comparison, ROI)
   - Forms that ask for too much information too early

CRITICAL INSTRUCTIONS:
- Quote ACTUAL CTAs, form labels, and page copy from the website.
- For every finding, explain the BUSINESS IMPACT (e.g., "This 9-field form likely loses 40-60% of visitors who start filling it out, representing significant pipeline leakage").
- Compare to BEST PRACTICES with named examples of companies doing it well.
- Write analysis_summary as a strategic narrative for a VP of Marketing, not a technical audit.

Provide a JSON response:
{{
    "overall_score": <number 0-100>,
    "score_items": [
        {{"name": "CTA Effectiveness & Hierarchy", "score": <0-100>, "max_score": 100, "weight": 1.8, "notes": "Quote actual CTAs and assess their value communication"}},
        {{"name": "Form Optimization", "score": <0-100>, "max_score": 100, "weight": 1.5, "notes": "Assess form length, field types, and conversion friction"}},
        {{"name": "Trust Signal Architecture", "score": <0-100>, "max_score": 100, "weight": 1.5, "notes": "Evaluate proof placement relative to conversion points"}},
        {{"name": "Buyer Journey Clarity", "score": <0-100>, "max_score": 100, "weight": 1.5, "notes": "How intuitive is the path from awareness to conversion?"}},
        {{"name": "Nurture Path Availability", "score": <0-100>, "max_score": 100, "weight": 1.2, "notes": "Options for visitors not ready to buy"}},
        {{"name": "Page-Level Conversion Design", "score": <0-100>, "max_score": 100, "weight": 1.0, "notes": "Do individual pages drive toward conversion?"}},
        {{"name": "Friction Reduction", "score": <0-100>, "max_score": 100, "weight": 1.0, "notes": "Dead ends, confusing paths, missing pages"}}
    ],
    "buyer_journey": {{
        "primary_path": ["Homepage", "Product Page", "Demo Request"],
        "clicks_to_conversion": <number>,
        "alternative_paths": [["path 2 steps"]],
        "friction_points": ["specific friction points along the journey with page references"],
        "missing_nurture_paths": ["content/resources that should exist but don't"],
        "dead_end_pages": ["pages with no clear next step"]
    }},
    "demo_page_teardown": {{
        "page_url": "URL of the primary conversion page",
        "form_fields_count": <number>,
        "form_fields": ["list of actual field labels"],
        "has_social_proof_near_form": true|false,
        "has_value_framing": true|false,
        "cta_text": "actual CTA button text",
        "trust_signals_present": ["list of trust elements near the form"],
        "assessment": "detailed assessment of the conversion page effectiveness",
        "suggested_cta": "concrete rewrite of the CTA with rationale"
    }},
    "funnel_analysis": {{
        "primary_cta": "the main conversion action with actual text",
        "secondary_ctas": ["other conversion paths with actual text"],
        "cta_consistency": "assessment of whether CTAs are consistent across pages",
        "funnel_stages_identified": ["awareness", "consideration", "decision"],
        "missing_stages": ["any gaps in the funnel with business impact"],
        "conversion_path_score": <0-10>
    }},
    "trust_architecture": {{
        "testimonials_count": <number>,
        "named_clients": true|false,
        "client_logos_visible": true|false,
        "case_studies_available": true|false,
        "third_party_badges": ["G2", "SOC 2", etc.],
        "proof_near_conversion": true|false,
        "trust_score": <0-10>,
        "assessment": "strategic assessment of trust architecture"
    }},
    "strengths": ["3-5 conversion strengths with specific quoted evidence"],
    "weaknesses": ["3-5 conversion weaknesses with business impact estimates"],
    "recommendations": [
        {{
            "issue": "specific conversion issue with quoted evidence from the site",
            "recommendation": "what to change, with concrete specifics",
            "business_impact": "estimated effect on conversion rate or pipeline (e.g., 'reducing form fields from 9 to 4 typically increases completion by 30-50%')",
            "before_example": "current CTA/form/copy quoted from the site",
            "after_example": "suggested replacement with rationale",
            "current_state": "description of current state",
            "best_practice": "named example of a company doing this well",
            "impact": "High|Medium|Low",
            "effort": "High|Medium|Low",
            "implementation_steps": ["step 1", "step 2", "step 3"],
            "success_metrics": ["metric to track improvement"],
            "timeline": "timeframe"
        }}
    ],
    "ab_test_ideas": [
        {{
            "test_name": "descriptive name",
            "hypothesis": "If we change X, Y will improve because Z",
            "control": "current state",
            "variant": "proposed change",
            "primary_metric": "what to measure",
            "expected_lift": "estimated improvement range"
        }}
    ],
    "analysis_summary": "3-4 paragraph strategic narrative written for a VP of Marketing. Frame the core conversion problem, explain what it's costing the business in pipeline, and paint a picture of what an optimized buyer journey would look like. Reference specific pages and CTAs from the site."
}}

Generate 6-10 specific, actionable conversion recommendations with quoted examples from the actual content."""


class ConversionAgent(BaseAgent):
    agent_name = "conversion"
    agent_display_name = "Conversion Optimization"
    dependencies = ["web_scraper", "screenshot"]

    async def run(self) -> dict[str, Any]:
        await self.update_progress(10, "Mapping conversion elements")

        site_structure = self._extract_site_structure()
        ctas = self._extract_all_ctas()
        forms = self._extract_all_forms()
        key_pages = self._extract_key_pages()
        tech_stack = self._extract_tech_stack()

        # Check for screenshot data
        screenshots = self._get_conversion_screenshots()

        prompt = CRO_PROMPT.format(
            company_url=self.context.company_url,
            site_structure=site_structure,
            ctas=ctas,
            forms=forms,
            key_pages=key_pages,
        )
        if tech_stack:
            prompt += f"\n\nDETECTED TECH STACK:\n{tech_stack}\nUse this to assess conversion infrastructure — are they using chatbots, analytics, A/B testing tools, retargeting pixels, etc.?"

        try:
            if screenshots:
                await self.update_progress(40, "Analyzing conversion elements with AI Vision")
                image_labels = "\n".join(f"- Image {i+1}: {s['label']}" for i, s in enumerate(screenshots))
                vision_addendum = (
                    f"\n\nI've also attached screenshots of key conversion elements. "
                    f"Analyze the visual effectiveness of CTAs, forms, and trust signals:\n{image_labels}\n"
                    f"Reference what you see in the screenshots in your analysis."
                )
                enhanced_prompt = prompt + vision_addendum
                vision_images = [{"base64": s["base64"], "media_type": "image/png"} for s in screenshots]
                response = await self.call_llm_vision(enhanced_prompt, vision_images, system=CRO_SYSTEM)
            else:
                await self.update_progress(40, "Analyzing conversion funnel with AI")
                response = await self.call_llm_json(prompt, system=CRO_SYSTEM)

            result = self.parse_json(response)

            if not result:
                return self._fallback_result()

            await self.update_progress(85, "Compiling CRO report")

            return {
                "score": result.get("overall_score", 50),
                "grade": None,
                "analysis_text": result.get("analysis_summary", ""),
                "recommendations": result.get("recommendations", []),
                "result_data": {
                    "score_items": result.get("score_items", []),
                    "buyer_journey": result.get("buyer_journey", {}),
                    "demo_page_teardown": result.get("demo_page_teardown", {}),
                    "funnel_analysis": result.get("funnel_analysis", {}),
                    "trust_architecture": result.get("trust_architecture", {}),
                    "ab_test_ideas": result.get("ab_test_ideas", []),
                    "strengths": result.get("strengths", []),
                    "weaknesses": result.get("weaknesses", []),
                    "recommendations": result.get("recommendations", []),
                    "vision_enabled": bool(screenshots),
                },
            }
        except Exception as e:
            logger.error(f"CRO analysis failed: {e}")
            return self._fallback_result()

    def _get_conversion_screenshots(self) -> list[dict]:
        """Get CTA and form screenshots for conversion analysis."""
        result = []
        for s in self.context.screenshots.values():
            if s.screenshot_type == "cta_primary" and s.base64_data:
                result.append({"base64": s.base64_data, "label": f"CTA on {s.page_type} page"})
                if len(result) >= 2:
                    break
        for s in self.context.screenshots.values():
            if s.screenshot_type == "form" and s.base64_data:
                result.append({"base64": s.base64_data, "label": f"Form on {s.page_type} page"})
                break
        for s in self.context.screenshots.values():
            if s.page_type == "pricing" and s.screenshot_type == "full_page" and s.base64_data:
                result.append({"base64": s.base64_data, "label": "Pricing page"})
                break
        return result[:4]

    def _extract_site_structure(self) -> str:
        page_types = {}
        for page in self.context.pages.values():
            pt = page.page_type or "other"
            page_types.setdefault(pt, []).append(page.url)
        lines = ["Site structure by page type:"]
        for pt, urls in page_types.items():
            lines.append(f"  {pt}: {len(urls)} pages")
            for url in urls[:3]:
                lines.append(f"    - {url}")
        return "\n".join(lines)

    def _extract_all_ctas(self) -> str:
        all_ctas = []
        for page in self.context.pages.values():
            for cta in page.ctas:
                all_ctas.append(
                    f"- [{page.page_type}] \"{cta.get('text', '')}\" -> {cta.get('href', '')}"
                )
        return "\n".join(all_ctas[:40]) or "No CTAs found."

    def _extract_all_forms(self) -> str:
        all_forms = []
        for page in self.context.pages.values():
            for form in page.forms:
                fields = form.get("fields", [])
                field_names = [f.get("name", f.get("type", "?")) for f in fields]
                all_forms.append(
                    f"- [{page.page_type}] {page.url}\n"
                    f"  Action: {form.get('action', 'N/A')}\n"
                    f"  Fields ({len(fields)}): {', '.join(field_names)}"
                )
        return "\n".join(all_forms[:15]) or "No forms found."

    def _extract_tech_stack(self) -> str:
        """Aggregate tech stack from all crawled pages."""
        all_tech: set[str] = set()
        for page in self.context.pages.values():
            all_tech.update(page.tech_stack)
        if not all_tech:
            return ""
        return "\n".join(f"- {t}" for t in sorted(all_tech))

    def _extract_key_pages(self) -> str:
        """Get content from conversion-critical pages."""
        priority = ["home", "pricing", "demo", "contact", "product"]
        lines = []
        for pt in priority:
            pages = self.context.get_pages_by_type(pt)
            for page in pages[:2]:
                lines.append(f"\n--- {pt.upper()}: {page.url} ---")
                lines.append(f"H1: {', '.join(page.h1_tags) or 'NONE'}")
                lines.append(f"Content: {page.raw_text[:2000]}")
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
            "analysis_text": "CRO analysis incomplete — LLM analysis unavailable.",
            "recommendations": [],
            "result_data": {"fallback": True, "strengths": [], "weaknesses": []},
        }

"""Visual & Design Agent — analyzes layout, color, typography, CTA design, and UX."""

import json
import logging
from typing import Any

from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

DESIGN_SYSTEM = """You are a senior UX/UI strategist who has redesigned 100+ B2B SaaS websites. You evaluate design not just for aesthetics but for its impact on conversion and trust. Every design choice either builds buyer confidence or erodes it — you identify which is happening and why. You reference specific pages and elements, compare to best-in-class B2B SaaS sites by name, and explain what each design issue is costing the business. Your analysis reads like a UX audit from a top design agency."""

DESIGN_PROMPT = """Analyze this B2B SaaS website's visual design and UX effectiveness.

Website: {company_url}

SITE STRUCTURE & CONTENT:
{site_data}

CTA ELEMENTS:
{ctas}

FORMS:
{forms}

IMAGE DATA:
{images}

CRITICAL INSTRUCTIONS:
- For every finding, explain the BUSINESS IMPACT — how the design choice affects conversion, trust, or engagement (e.g., "The lack of visual hierarchy in the hero section means visitors take 5-8 seconds to understand the value prop, increasing bounce rate by an estimated 15-20%").
- Reference SPECIFIC pages and elements from the data provided.
- Compare to BEST PRACTICES with named examples of well-designed B2B SaaS sites.
- For each recommendation, describe the BEFORE state and AFTER state concretely.
- Write analysis_summary as a strategic narrative for a marketing leader, not a design checklist.

Provide a JSON response:
{{
    "overall_score": <number 0-100>,
    "score_items": [
        {{"name": "Visual Hierarchy", "score": <0-100>, "max_score": 100, "weight": 1.5, "notes": "Assess how effectively the eye is guided to key messages and CTAs"}},
        {{"name": "CTA Design & Placement", "score": <0-100>, "max_score": 100, "weight": 1.5, "notes": "Quote actual CTAs and assess their visual prominence and placement"}},
        {{"name": "Content Layout", "score": <0-100>, "max_score": 100, "weight": 1.2, "notes": "Assess scannability, whitespace, and content organization"}},
        {{"name": "Imagery & Media Quality", "score": <0-100>, "max_score": 100, "weight": 1.0, "notes": "Assess whether images build trust or feel generic"}},
        {{"name": "Navigation & Information Architecture", "score": <0-100>, "max_score": 100, "weight": 1.3, "notes": "Assess whether visitors can find what they need quickly"}},
        {{"name": "Trust Indicators Design", "score": <0-100>, "max_score": 100, "weight": 1.0, "notes": "Assess visual treatment of logos, testimonials, security badges"}},
        {{"name": "Form Design", "score": <0-100>, "max_score": 100, "weight": 1.0, "notes": "Assess form UX, field count, and visual treatment"}},
        {{"name": "Overall Visual Polish", "score": <0-100>, "max_score": 100, "weight": 1.0, "notes": "Does the site feel premium and professional?"}}
    ],
    "strengths": ["3-5 design strengths with specific evidence and business impact"],
    "weaknesses": ["3-5 design weaknesses with estimated conversion impact"],
    "recommendations": [
        {{
            "issue": "specific design issue with page reference",
            "recommendation": "what to change with concrete specifics",
            "business_impact": "estimated effect on conversion or engagement",
            "before_example": "description of current design state",
            "after_example": "description of recommended design change",
            "current_state": "current design description",
            "best_practice": "named example of a B2B SaaS site doing this well",
            "impact": "High|Medium|Low",
            "effort": "High|Medium|Low",
            "implementation_steps": ["step 1", "step 2", "step 3"],
            "success_metrics": ["metric to track improvement"],
            "timeline": "timeframe"
        }}
    ],
    "analysis_summary": "3-4 paragraph design analysis as a strategic narrative. Frame how design choices affect buyer confidence and conversion, not just aesthetics."
}}

Generate 5-8 specific, actionable design recommendations with before/after descriptions."""


class VisualDesignAgent(BaseAgent):
    agent_name = "visual_design"
    agent_display_name = "Visual & Design"
    dependencies = ["web_scraper", "screenshot"]

    async def run(self) -> dict[str, Any]:
        await self.update_progress(10, "Extracting design data")

        site_data = self._extract_design_data()
        ctas = self._extract_cta_details()
        forms = self._extract_form_details()
        images = self._extract_image_details()

        # Check for screenshots from screenshot agent
        screenshots = self._get_key_screenshots()

        if screenshots:
            await self.update_progress(40, "Analyzing design with AI Vision")
            return await self._run_vision_analysis(site_data, ctas, forms, images, screenshots)
        else:
            await self.update_progress(40, "Analyzing design with AI (text-only)")
            return await self._run_text_analysis(site_data, ctas, forms, images)

    def _get_key_screenshots(self) -> list[dict]:
        """Get the most relevant screenshots for visual analysis."""
        result = []

        # Homepage full page
        for s in self.context.screenshots.values():
            if s.page_type == "home" and s.screenshot_type == "full_page" and s.base64_data:
                result.append({"base64": s.base64_data, "media_type": "image/png", "label": "Homepage (full page)"})
                break

        # Homepage hero
        for s in self.context.screenshots.values():
            if s.page_type == "home" and s.screenshot_type == "hero" and s.base64_data:
                result.append({"base64": s.base64_data, "media_type": "image/png", "label": "Homepage hero section"})
                break

        # Navigation
        for s in self.context.screenshots.values():
            if s.screenshot_type == "nav" and s.base64_data:
                result.append({"base64": s.base64_data, "media_type": "image/png", "label": "Navigation bar"})
                break

        # CTA
        for s in self.context.screenshots.values():
            if s.screenshot_type == "cta_primary" and s.base64_data:
                result.append({"base64": s.base64_data, "media_type": "image/png", "label": "Primary CTA"})
                break

        # Mobile
        for s in self.context.screenshots.values():
            if s.screenshot_type == "mobile_full" and s.base64_data:
                result.append({"base64": s.base64_data, "media_type": "image/png", "label": "Mobile homepage"})
                break

        return result[:5]

    async def _run_vision_analysis(
        self, site_data: str, ctas: str, forms: str, images: str, screenshots: list[dict]
    ) -> dict[str, Any]:
        """Analyze design using Claude Vision with actual screenshots."""
        image_labels = "\n".join(f"- Image {i+1}: {s['label']}" for i, s in enumerate(screenshots))

        prompt = f"""Analyze this B2B SaaS website's visual design based on the actual screenshots provided.

Website: {self.context.company_url}

SCREENSHOTS PROVIDED:
{image_labels}

EXTRACTED SITE DATA:
{site_data}

CTA ELEMENTS:
{ctas}

FORMS:
{forms}

IMAGE DATA:
{images}

CRITICAL INSTRUCTIONS:
- For every finding, explain the BUSINESS IMPACT — how the design choice affects conversion and trust (e.g., "The low-contrast CTA button blends into the hero section, likely reducing click-through by 15-25%").
- Reference what you ACTUALLY SEE in the screenshots — colors, layout, spacing, visual hierarchy.
- Compare to BEST PRACTICES with named examples of well-designed B2B SaaS sites.
- For each recommendation, describe the BEFORE (what you see) and AFTER (what it should look like).

Based on what you SEE in the screenshots AND the extracted data, provide a JSON response:
{{
    "overall_score": <number 0-100>,
    "score_items": [
        {{"name": "Visual Hierarchy", "score": <0-100>, "max_score": 100, "weight": 1.5, "notes": "Assess how effectively the eye is guided to key messages and CTAs"}},
        {{"name": "CTA Design & Placement", "score": <0-100>, "max_score": 100, "weight": 1.5, "notes": "Describe the actual CTA appearance and assess visual prominence"}},
        {{"name": "Content Layout", "score": <0-100>, "max_score": 100, "weight": 1.2, "notes": "Assess scannability, whitespace, and content organization"}},
        {{"name": "Imagery & Media Quality", "score": <0-100>, "max_score": 100, "weight": 1.0, "notes": "Assess whether images build trust or feel generic"}},
        {{"name": "Navigation & Information Architecture", "score": <0-100>, "max_score": 100, "weight": 1.3, "notes": "Assess navigation clarity and findability"}},
        {{"name": "Trust Indicators Design", "score": <0-100>, "max_score": 100, "weight": 1.0, "notes": "Assess visual treatment of logos, testimonials, badges"}},
        {{"name": "Form Design", "score": <0-100>, "max_score": 100, "weight": 1.0, "notes": "Assess form UX and visual treatment"}},
        {{"name": "Overall Visual Polish", "score": <0-100>, "max_score": 100, "weight": 1.0, "notes": "Does the site feel premium and professional?"}}
    ],
    "visual_observations": ["list of specific things you observe in the screenshots"],
    "strengths": ["3-5 design strengths with specific visual evidence and business impact"],
    "weaknesses": ["3-5 design weaknesses with estimated conversion impact"],
    "recommendations": [
        {{
            "issue": "specific design issue observed in screenshots",
            "recommendation": "what to change with concrete specifics",
            "business_impact": "estimated effect on conversion or engagement",
            "before_example": "description of current design as seen in screenshot",
            "after_example": "description of recommended design change",
            "current_state": "current design as seen in screenshot",
            "best_practice": "named example of a B2B SaaS site doing this well",
            "impact": "High|Medium|Low",
            "effort": "High|Medium|Low",
            "implementation_steps": ["step 1", "step 2", "step 3"],
            "success_metrics": ["metric to track improvement"],
            "timeline": "timeframe"
        }}
    ],
    "analysis_summary": "3-4 paragraph design analysis referencing what you see in the screenshots. Frame design as a conversion driver, not just aesthetics."
}}

Generate 5-8 specific, actionable design recommendations based on visual evidence."""

        try:
            vision_images = [{"base64": s["base64"], "media_type": s.get("media_type", "image/png")} for s in screenshots]
            response = await self.call_llm_vision(prompt, vision_images, system=DESIGN_SYSTEM)
            result = self.parse_json(response)

            if not result:
                logger.warning("Vision analysis returned unparseable JSON, falling back to text")
                return await self._run_text_analysis(site_data, ctas, forms, images)

            await self.update_progress(85, "Compiling design report")

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
                    "visual_observations": result.get("visual_observations", []),
                    "vision_enabled": True,
                },
            }
        except Exception as e:
            logger.error(f"Vision design analysis failed: {e}, falling back to text-only")
            return await self._run_text_analysis(site_data, ctas, forms, images)

    async def _run_text_analysis(
        self, site_data: str, ctas: str, forms: str, images: str
    ) -> dict[str, Any]:
        """Original text-only analysis path."""
        prompt = DESIGN_PROMPT.format(
            company_url=self.context.company_url,
            site_data=site_data,
            ctas=ctas,
            forms=forms,
            images=images,
        )

        try:
            response = await self.call_llm_json(prompt, system=DESIGN_SYSTEM)
            result = self.parse_json(response)

            if not result:
                return self._fallback_result()

            await self.update_progress(85, "Compiling design report")

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
                },
            }
        except Exception as e:
            logger.error(f"Design analysis failed: {e}")
            return self._fallback_result()

    def _extract_design_data(self) -> str:
        lines = []
        for url, page in list(self.context.pages.items())[:15]:
            lines.append(f"\n--- {page.page_type.upper()}: {url} ---")
            lines.append(f"Title: {page.title}")
            lines.append(f"H1: {', '.join(page.h1_tags) or 'NONE'}")
            lines.append(f"H2 Count: {len(page.h2_tags)}")
            lines.append(f"Images: {len(page.images)}")
            lines.append(f"CTAs: {len(page.ctas)}")
            lines.append(f"Forms: {len(page.forms)}")
            lines.append(f"Content preview: {page.raw_text[:500]}")
        return "\n".join(lines)[:15000]

    def _extract_cta_details(self) -> str:
        all_ctas = []
        for page in self.context.pages.values():
            for cta in page.ctas:
                all_ctas.append(
                    f"- [{page.page_type}] {cta.get('text', '')} "
                    f"(href: {cta.get('href', '')})"
                )
        return "\n".join(all_ctas[:30]) or "No CTAs found."

    def _extract_form_details(self) -> str:
        all_forms = []
        for page in self.context.pages.values():
            for form in page.forms:
                fields = [
                    f"{f.get('name', 'unnamed')} ({f.get('type', 'text')})"
                    for f in form.get("fields", [])
                ]
                all_forms.append(
                    f"- [{page.page_type}] {len(fields)} fields: {', '.join(fields)}"
                )
        return "\n".join(all_forms[:15]) or "No forms found."

    def _extract_image_details(self) -> str:
        stats = {"total": 0, "with_alt": 0, "without_alt": 0}
        for page in self.context.pages.values():
            for img in page.images:
                stats["total"] += 1
                if img.get("alt"):
                    stats["with_alt"] += 1
                else:
                    stats["without_alt"] += 1
        return (
            f"Total images: {stats['total']}, "
            f"With alt text: {stats['with_alt']}, "
            f"Without alt text: {stats['without_alt']}"
        )

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
            "analysis_text": "Design analysis incomplete — LLM analysis unavailable.",
            "recommendations": [],
            "result_data": {"fallback": True, "strengths": [], "weaknesses": []},
        }

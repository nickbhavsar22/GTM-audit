"""Visual & Design Agent — analyzes layout, color, typography, CTA design, and UX."""

import json
import logging
from typing import Any

from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

DESIGN_SYSTEM = """You are an expert UX/UI designer and web design analyst specializing in B2B SaaS websites.
Analyze the provided website structure and content for design effectiveness, visual hierarchy,
and conversion-oriented design patterns. Reference specific pages and elements."""

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

Provide a JSON response:
{{
    "overall_score": <number 0-100>,
    "score_items": [
        {{"name": "Visual Hierarchy", "score": <0-100>, "max_score": 100, "weight": 1.5, "notes": "..."}},
        {{"name": "CTA Design & Placement", "score": <0-100>, "max_score": 100, "weight": 1.5, "notes": "..."}},
        {{"name": "Content Layout", "score": <0-100>, "max_score": 100, "weight": 1.2, "notes": "..."}},
        {{"name": "Imagery & Media Quality", "score": <0-100>, "max_score": 100, "weight": 1.0, "notes": "..."}},
        {{"name": "Navigation & Information Architecture", "score": <0-100>, "max_score": 100, "weight": 1.3, "notes": "..."}},
        {{"name": "Trust Indicators Design", "score": <0-100>, "max_score": 100, "weight": 1.0, "notes": "..."}},
        {{"name": "Form Design", "score": <0-100>, "max_score": 100, "weight": 1.0, "notes": "..."}},
        {{"name": "Overall Visual Polish", "score": <0-100>, "max_score": 100, "weight": 1.0, "notes": "..."}}
    ],
    "strengths": ["3-5 design strengths with specific evidence"],
    "weaknesses": ["3-5 design weaknesses with specific evidence"],
    "recommendations": [
        {{
            "issue": "specific design issue",
            "recommendation": "what to change",
            "current_state": "current design description",
            "best_practice": "design best practice",
            "impact": "High|Medium|Low",
            "effort": "High|Medium|Low",
            "implementation_steps": ["step 1", "step 2", "step 3"],
            "success_metrics": ["metric 1"],
            "timeline": "timeframe"
        }}
    ],
    "analysis_summary": "2-3 paragraph design analysis"
}}

Generate 5-8 specific, actionable design recommendations."""


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

Based on what you SEE in the screenshots AND the extracted data, provide a JSON response:
{{
    "overall_score": <number 0-100>,
    "score_items": [
        {{"name": "Visual Hierarchy", "score": <0-100>, "max_score": 100, "weight": 1.5, "notes": "..."}},
        {{"name": "CTA Design & Placement", "score": <0-100>, "max_score": 100, "weight": 1.5, "notes": "..."}},
        {{"name": "Content Layout", "score": <0-100>, "max_score": 100, "weight": 1.2, "notes": "..."}},
        {{"name": "Imagery & Media Quality", "score": <0-100>, "max_score": 100, "weight": 1.0, "notes": "..."}},
        {{"name": "Navigation & Information Architecture", "score": <0-100>, "max_score": 100, "weight": 1.3, "notes": "..."}},
        {{"name": "Trust Indicators Design", "score": <0-100>, "max_score": 100, "weight": 1.0, "notes": "..."}},
        {{"name": "Form Design", "score": <0-100>, "max_score": 100, "weight": 1.0, "notes": "..."}},
        {{"name": "Overall Visual Polish", "score": <0-100>, "max_score": 100, "weight": 1.0, "notes": "..."}}
    ],
    "visual_observations": ["list of specific things you observe in the screenshots"],
    "strengths": ["3-5 design strengths with specific visual evidence"],
    "weaknesses": ["3-5 design weaknesses with specific visual evidence"],
    "recommendations": [
        {{
            "issue": "specific design issue observed in screenshots",
            "recommendation": "what to change",
            "current_state": "current design as seen in screenshot",
            "best_practice": "design best practice",
            "impact": "High|Medium|Low",
            "effort": "High|Medium|Low",
            "implementation_steps": ["step 1", "step 2", "step 3"],
            "success_metrics": ["metric 1"],
            "timeline": "timeframe"
        }}
    ],
    "analysis_summary": "2-3 paragraph design analysis referencing what you see in the screenshots"
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

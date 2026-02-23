"""Messaging & Positioning Agent — analyzes value proposition, headlines, and messaging clarity."""

import json
import logging
from typing import Any

from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

MESSAGING_SYSTEM = """You are a senior B2B SaaS marketing strategist who has audited 200+ company websites for messaging effectiveness. You write like a $10K consultant — every finding is specific, evidence-based, and tied to business impact. You quote actual copy from the website and explain not just what's wrong, but what it's costing the business in pipeline and conversion. Your analysis should feel like it came from a trusted advisor who deeply understands B2B buyer psychology, not a crawl tool.

You are a senior B2B marketing consultant. Write findings in terms of pipeline, revenue, and buyer behavior — not technical implementation details. Be specific to this company. Avoid generic consulting language like 'leverage' and 'optimize.' Conservative and transparent beats optimistic and unsupported. Show your calculation for any projected outcome."""

MESSAGING_PROMPT = """Perform a comprehensive messaging and positioning audit for this B2B SaaS company's website. This is the centerpiece section of a premium GTM audit report.

Website: {company_url}
Company Name: {company_name}

HOMEPAGE & KEY PAGE CONTENT:
{content}

CTAs FOUND:
{ctas}

TESTIMONIALS:
{testimonials}

YOUR ANALYSIS MUST INCLUDE:

1. **Homepage Messaging Teardown**: Walk through the actual headline hierarchy (H1, H2s, supporting copy). Quote the real text. Explain what's working and what creates confusion for a first-time visitor.

2. **Message Collision Analysis**: Identify where the site tries to be multiple things at once (e.g., platform AND services AND thought leader). Quote the competing messages and explain why this creates buyer hesitation.

3. **Messaging Clarity Test**: Score how quickly a first-time visitor can answer three questions:
   - "What do you do?" (0-10)
   - "Who is it for?" (0-10)
   - "Why should I care?" (0-10)
   Provide evidence for each score.

4. **Social Proof Gap Analysis**: Evaluate whether stated proof (logos, metrics, testimonials) is substantiated. If they claim Fortune 500 clients but show no logos, flag the trust deficit.

5. **Before/After Suggestions**: For each weak headline or CTA, provide a concrete rewrite with rationale.

CRITICAL INSTRUCTIONS:
- Quote ACTUAL COPY from the website in your analysis. Don't paraphrase.
- For every finding, explain the BUSINESS IMPACT (e.g., "This fragmented messaging likely increases bounce rate by 15-25% because visitors can't quickly determine relevance").
- Compare to BEST PRACTICES with named examples of companies doing it well.
- Write analysis_summary as a strategic narrative for a CMO, not a list of findings.

Provide a JSON response:
{{
    "overall_score": <number 0-100>,
    "score_items": [
        {{"name": "Value Proposition Clarity", "score": <0-100>, "max_score": 100, "weight": 2.0, "notes": "Quote the actual value prop and assess clarity"}},
        {{"name": "Homepage Messaging Hierarchy", "score": <0-100>, "max_score": 100, "weight": 1.8, "notes": "Assess the H1→H2→CTA flow"}},
        {{"name": "Competitive Differentiation", "score": <0-100>, "max_score": 100, "weight": 1.5, "notes": "How clearly do they stand apart from alternatives?"}},
        {{"name": "Target Audience Specificity", "score": <0-100>, "max_score": 100, "weight": 1.5, "notes": "Can a visitor quickly tell if this is for them?"}},
        {{"name": "Social Proof Effectiveness", "score": <0-100>, "max_score": 100, "weight": 1.3, "notes": "Quality and placement of proof elements"}},
        {{"name": "CTA Value Framing", "score": <0-100>, "max_score": 100, "weight": 1.3, "notes": "Do CTAs communicate value, not just action?"}},
        {{"name": "Benefit-Led vs Feature-Led Balance", "score": <0-100>, "max_score": 100, "weight": 1.0, "notes": "Are they leading with outcomes or features?"}},
        {{"name": "Message Consistency Across Pages", "score": <0-100>, "max_score": 100, "weight": 1.0, "notes": "Does the story hold across pages?"}}
    ],
    "homepage_teardown": {{
        "h1_text": "the actual H1 text from the homepage",
        "h1_assessment": "detailed assessment of why it works or doesn't, with business impact",
        "h2_texts": ["actual H2 texts from homepage"],
        "messaging_hierarchy_assessment": "how the H1→H2→CTA flow works or breaks down",
        "suggested_h1": "concrete rewrite of the H1 with rationale",
        "suggested_subheadline": "concrete supporting subheadline suggestion"
    }},
    "message_collisions": [
        {{
            "message_a": "quoted text from site",
            "message_b": "conflicting quoted text from site",
            "conflict": "why these messages compete with each other",
            "resolution": "how to resolve the conflict"
        }}
    ],
    "messaging_clarity_score": {{
        "what_you_do": {{"score": <0-10>, "evidence": "what a visitor sees and how quickly they understand"}},
        "who_its_for": {{"score": <0-10>, "evidence": "how clearly the target audience is defined"}},
        "why_care": {{"score": <0-10>, "evidence": "how compelling the differentiation and urgency is"}}
    }},
    "current_value_proposition": "their current value prop as stated on site",
    "suggested_value_proposition": "your recommended value prop rewrite",
    "messaging_pillars": ["list of key messaging pillars/themes identified"],
    "strengths": ["3-5 messaging strengths with specific quoted evidence"],
    "weaknesses": ["3-5 messaging weaknesses with business impact estimates"],
    "recommendations": [
        {{
            "issue": "specific issue with quoted example from the site",
            "recommendation": "what to change, with concrete new copy",
            "business_impact": "estimated effect on conversion/pipeline (e.g., 'likely increasing bounce rate by 15-25%')",
            "before_example": "current copy quoted from the site",
            "after_example": "suggested replacement copy",
            "current_state": "description of current state",
            "best_practice": "named example of a company doing this well",
            "impact": "High|Medium|Low",
            "effort": "High|Medium|Low",
            "implementation_steps": ["step 1", "step 2", "step 3"],
            "success_metrics": ["metric to track improvement"],
            "timeline": "timeframe"
        }}
    ],
    "analysis_summary": "3-4 paragraph strategic narrative written for a CMO. Frame the core messaging problem, explain what it's costing the business, and paint a picture of what great messaging would look like for this company. Reference specific copy from the site."
}}

Generate 6-10 specific, actionable recommendations with quoted examples from the actual content."""


class MessagingAgent(BaseAgent):
    agent_name = "messaging"
    agent_display_name = "Messaging & Positioning"
    dependencies = ["web_scraper", "screenshot"]

    async def run(self) -> dict[str, Any]:
        await self.update_progress(10, "Extracting messaging data")

        content = self._extract_messaging_data()
        ctas = self._extract_ctas()
        testimonials = self._extract_testimonials()

        # Check for screenshot data
        screenshots = self._get_messaging_screenshots()

        prompt = MESSAGING_PROMPT.format(
            company_url=self.context.company_url,
            company_name=self.context.company_name or "Unknown",
            content=content,
            ctas=ctas,
            testimonials=testimonials,
        )

        try:
            if screenshots:
                await self.update_progress(40, "Sending to AI Vision for messaging analysis")
                image_labels = "\n".join(f"- Image {i+1}: {s['label']}" for i, s in enumerate(screenshots))
                vision_addendum = (
                    f"\n\nI've also attached screenshots of the website. "
                    f"Analyze the visual presentation of the messaging:\n{image_labels}\n"
                    f"Reference what you see in the screenshots in your analysis."
                )
                enhanced_prompt = prompt + vision_addendum
                vision_images = [{"base64": s["base64"], "media_type": "image/png"} for s in screenshots]
                response = await self.call_llm_vision(enhanced_prompt, vision_images, system=MESSAGING_SYSTEM)
            else:
                await self.update_progress(40, "Sending to AI for messaging analysis")
                response = await self.call_llm_json(prompt, system=MESSAGING_SYSTEM)

            await self.update_progress(70, "Parsing AI messaging response")
            result = self.parse_json(response)

            if not result:
                logger.error(f"Messaging JSON parse failed. Response preview: {response[:500]}")
                self._last_error = f"JSON parse failed. Response starts: {response[:200]}"
                return self._fallback_result()

            await self.update_progress(85, "Compiling messaging report")

            # Add screenshot_ref to headline recommendations
            recs = result.get("recommendations", [])
            for rec in recs:
                if isinstance(rec, dict):
                    issue_lower = rec.get("issue", "").lower()
                    if "headline" in issue_lower or "value prop" in issue_lower or "h1" in issue_lower:
                        rec["screenshot_ref"] = "homepage_hero"

            return {
                "score": result.get("overall_score", 50),
                "grade": None,
                "analysis_text": result.get("analysis_summary", ""),
                "recommendations": recs,
                "result_data": {
                    "score_items": result.get("score_items", []),
                    "strengths": result.get("strengths", []),
                    "weaknesses": result.get("weaknesses", []),
                    "current_value_proposition": result.get("current_value_proposition", ""),
                    "suggested_value_proposition": result.get("suggested_value_proposition", ""),
                    "messaging_pillars": result.get("messaging_pillars", []),
                    "homepage_teardown": result.get("homepage_teardown", {}),
                    "message_collisions": result.get("message_collisions", []),
                    "messaging_clarity_score": result.get("messaging_clarity_score", {}),
                    "recommendations": recs,
                    "vision_enabled": bool(screenshots),
                },
            }
        except Exception as e:
            logger.error(f"Messaging analysis failed: {e}")
            return self._fallback_result()

    def _get_messaging_screenshots(self) -> list[dict]:
        """Get hero and headline screenshots for messaging analysis."""
        result = []
        for s in self.context.screenshots.values():
            if s.page_type == "home" and s.screenshot_type == "hero" and s.base64_data:
                result.append({"base64": s.base64_data, "label": "Homepage hero section"})
                break
        for s in self.context.screenshots.values():
            if s.page_type == "home" and s.screenshot_type == "h1" and s.base64_data:
                result.append({"base64": s.base64_data, "label": "Homepage primary headline"})
                break
        for s in self.context.screenshots.values():
            if s.page_type == "home" and s.screenshot_type == "full_page" and s.base64_data:
                result.append({"base64": s.base64_data, "label": "Homepage full page"})
                break
        return result[:3]

    def _extract_messaging_data(self) -> str:
        """Extract messaging-relevant content from key pages."""
        lines = []
        # Prioritize homepage and product pages
        priority_types = ["home", "product", "pricing", "about", "customers"]
        sorted_pages = sorted(
            self.context.pages.values(),
            key=lambda p: (
                priority_types.index(p.page_type)
                if p.page_type in priority_types
                else 99
            ),
        )

        for page in sorted_pages[:10]:
            lines.append(f"\n--- {page.page_type.upper()}: {page.url} ---")
            lines.append(f"Title: {page.title}")
            if page.h1_tags:
                lines.append(f"H1: {' | '.join(page.h1_tags)}")
            if page.h2_tags:
                lines.append(f"H2s: {' | '.join(page.h2_tags[:8])}")
            lines.append(f"Content:\n{page.raw_text[:3000]}")

        return "\n".join(lines)[:20000]

    def _extract_ctas(self) -> str:
        """Extract all CTAs from the site."""
        all_ctas = []
        for page in self.context.pages.values():
            for cta in page.ctas:
                text = cta.get("text", "").strip()
                if text and text not in all_ctas:
                    all_ctas.append(text)
        return "\n".join(f"- {cta}" for cta in all_ctas[:30])

    def _extract_testimonials(self) -> str:
        all_testimonials = []
        for page in self.context.pages.values():
            all_testimonials.extend(page.testimonials)
        if not all_testimonials:
            return "No testimonials found on the website."
        return "\n".join(f"- {t[:200]}" for t in all_testimonials[:10])

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
            "analysis_text": "Messaging analysis incomplete — LLM analysis unavailable.",
            "recommendations": [],
            "result_data": {"fallback": True, "strengths": [], "weaknesses": []},
        }

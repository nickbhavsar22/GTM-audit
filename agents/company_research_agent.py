"""Company Research Agent — builds a structured company profile using scraped data + Claude."""

import json
import logging
from typing import Any

from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

COMPANY_RESEARCH_SYSTEM = """You are a B2B SaaS company research analyst. Analyze the provided website content
and extract a comprehensive company profile. Be factual — only report what you can confirm from the content.
If information is not available, use null. Do not invent data."""

COMPANY_RESEARCH_PROMPT = """Analyze this company's website content and extract a structured company profile.

Website: {company_url}

SCRAPED CONTENT:
{content}

Return a JSON object with this structure:
{{
    "company_name": "string",
    "tagline": "string or null",
    "description": "1-2 sentence description of what the company does",
    "industry": "string (e.g., 'Marketing Technology', 'Sales Enablement')",
    "category": "string (e.g., 'CRM', 'Analytics', 'Automation')",
    "target_market": "B2B, B2C, or Both",
    "company_size_indicators": "startup, growth, enterprise — based on evidence",
    "value_proposition": "their primary value proposition",
    "products": ["list of products/services mentioned"],
    "target_audience": {{
        "industries": ["list of target industries mentioned"],
        "company_sizes": ["SMB", "Mid-Market", "Enterprise"],
        "roles": ["list of target job roles/titles mentioned"]
    }},
    "proof_points": {{
        "customer_logos": ["list of customer names shown"],
        "metrics": ["list of quantitative claims, e.g., '10x faster'"],
        "awards": ["list of awards/certifications"],
        "integrations": ["list of integrations mentioned"]
    }},
    "content_strategy": {{
        "has_blog": true/false,
        "has_case_studies": true/false,
        "has_resources": true/false,
        "has_documentation": true/false,
        "content_themes": ["list of main content themes"]
    }},
    "business_model": {{
        "pricing_model": "freemium/free-trial/demo-request/contact-sales/unknown",
        "has_pricing_page": true/false
    }},
    "technology_stack": ["any technologies detected from the website"]
}}"""


class CompanyResearchAgent(BaseAgent):
    agent_name = "company_research"
    agent_display_name = "Company Research"
    dependencies = ["web_scraper"]

    async def run(self) -> dict[str, Any]:
        """Analyze scraped content to build company profile."""
        await self.update_progress(10, "Analyzing website content")

        content = self.get_all_pages_content(max_chars=20000)
        if not content:
            return self._empty_result("No scraped content available")

        await self.update_progress(30, "Building company profile with AI")

        prompt = COMPANY_RESEARCH_PROMPT.format(
            company_url=self.context.company_url,
            content=content,
        )

        try:
            response = await self.call_llm_json(prompt, system=COMPANY_RESEARCH_SYSTEM)

            # Parse JSON from response
            profile = self.parse_json(response)
            if not profile:
                logger.error(f"Company profile JSON parse failed. Response preview: {response[:500]}")
                self._last_error = f"JSON parse failed. Response starts: {response[:200]}"
                return self._empty_result("Failed to parse company profile")

            # Store in context for other agents
            self.context.company_profile = profile

            # Update company name if found
            if profile.get("company_name"):
                self.context.company_name = profile["company_name"]

            await self.update_progress(80, "Generating company analysis")

            analysis_text = self._generate_analysis_text(profile)

            return {
                "score": None,  # Research agent doesn't score
                "grade": None,
                "analysis_text": analysis_text,
                "recommendations": [],
                "result_data": profile,
            }

        except Exception as e:
            logger.error(f"Company research failed: {e}")
            return self._empty_result(str(e))

    def _parse_json(self, text: str) -> dict | None:
        """Extract JSON from LLM response."""
        # Try direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try to find JSON block
        import re

        json_match = re.search(r"\{[\s\S]*\}", text)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        logger.warning("Failed to parse JSON from LLM response")
        return None

    def _generate_analysis_text(self, profile: dict) -> str:
        """Generate human-readable analysis from the profile."""
        name = profile.get("company_name", "The company")
        desc = profile.get("description", "")
        industry = profile.get("industry", "Unknown")
        target = profile.get("target_market", "Unknown")
        vp = profile.get("value_proposition", "")

        lines = [
            f"**{name}** operates in the {industry} space, targeting {target} markets.",
        ]
        if desc:
            lines.append(f"\n{desc}")
        if vp:
            lines.append(f"\n**Value Proposition:** {vp}")

        # Target audience
        ta = profile.get("target_audience", {})
        if ta.get("industries"):
            lines.append(f"\n**Target Industries:** {', '.join(ta['industries'][:5])}")
        if ta.get("roles"):
            lines.append(f"\n**Target Roles:** {', '.join(ta['roles'][:5])}")

        # Proof points
        pp = profile.get("proof_points", {})
        if pp.get("customer_logos"):
            lines.append(
                f"\n**Notable Customers:** {', '.join(pp['customer_logos'][:8])}"
            )
        if pp.get("metrics"):
            lines.append(f"\n**Key Metrics:** {', '.join(pp['metrics'][:5])}")

        return "\n".join(lines)

    def _empty_result(self, reason: str) -> dict[str, Any]:
        return {
            "score": None,
            "grade": None,
            "analysis_text": f"Company research incomplete: {reason}",
            "recommendations": [],
            "result_data": {"error": reason},
        }

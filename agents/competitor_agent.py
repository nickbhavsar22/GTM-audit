"""Competitor Intelligence Agent — identifies and analyzes 5-10 competitors."""

import json
import logging
from typing import Any

from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

COMPETITOR_SYSTEM = """You are a senior competitive intelligence strategist who has mapped competitive landscapes for 100+ B2B SaaS companies. You think like a PE firm doing due diligence — you assess competitive moats, identify positioning gaps, and explain exactly where the company is winning and losing deals. You name real companies, cite specific positioning statements, and explain what each competitor's existence means for the target company's GTM strategy. Your analysis reads like a $15K competitive brief, not a Google search summary.

You are a senior B2B marketing consultant. Write findings in terms of pipeline, revenue, and buyer behavior — not technical implementation details. Be specific to this company. Avoid generic consulting language like 'leverage' and 'optimize.' Conservative and transparent beats optimistic and unsupported. Show your calculation for any projected outcome."""

COMPETITOR_PROMPT = """Perform a comprehensive competitive intelligence analysis for this B2B SaaS company. This section of the GTM audit should give the reader a complete picture of their competitive landscape and strategic positioning.

Website: {company_url}
Company Name: {company_name}

COMPANY PROFILE:
{company_profile}

WEBSITE CONTENT (key pages):
{content}

YOUR ANALYSIS MUST INCLUDE:

1. **Competitor Identification**: Identify 4-8 real, named competitors. For each, explain WHY they compete (overlapping ICP, similar features, same budget line item) rather than just listing names.

2. **Positioning Comparison**: For each competitor, quote or summarize their actual positioning statement from their website and compare it to {company_name}'s positioning. Explain who wins in a head-to-head evaluation and why.

3. **Feature/Capability Matrix**: Identify 5-8 key capability areas for this market category. Assess which competitors have strength in each area (even if inferred from their website copy, not verified firsthand).

4. **Positioning Map**: Place {company_name} and all competitors on two strategic axes relevant to this market (e.g., "Enterprise ←→ SMB" and "Platform ←→ Point Solution", or "Self-Serve ←→ Sales-Led" and "Vertical ←→ Horizontal"). Choose axes that reveal meaningful strategic differentiation.

5. **Competitive Messaging Analysis**: How does each competitor frame their value proposition differently? What language patterns do they use? Where does {company_name}'s messaging blend in vs. stand out?

6. **Win/Loss Indicators**: Based on positioning and messaging strength, where is {company_name} likely winning deals vs. losing them? What buyer segments are most/least contested?

CRITICAL INSTRUCTIONS:
- Name REAL competitors — don't use placeholders like "Competitor A". Use your knowledge of B2B SaaS markets.
- For every finding, explain the BUSINESS IMPACT (e.g., "This positioning overlap means {company_name} likely loses 20-30% of evaluations where buyers see no differentiation").
- Quote ACTUAL positioning language from {company_name}'s website and compare to how competitors frame similar capabilities.
- Write analysis_summary as a strategic brief for a CEO, not a list of competitors.

Provide a JSON response:
{{
    "overall_score": <number 0-100 based on competitive positioning strength>,
    "score_items": [
        {{"name": "Market Positioning Clarity", "score": <0-100>, "max_score": 100, "weight": 1.5, "notes": "How clearly does their positioning differentiate from competitors?"}},
        {{"name": "Competitive Differentiation", "score": <0-100>, "max_score": 100, "weight": 2.0, "notes": "Do they have a defensible competitive moat or unique angle?"}},
        {{"name": "Category Authority", "score": <0-100>, "max_score": 100, "weight": 1.3, "notes": "Do they own a category or subcategory, or are they one of many?"}},
        {{"name": "Feature/Benefit Communication vs Competitors", "score": <0-100>, "max_score": 100, "weight": 1.2, "notes": "How well do they articulate advantages over alternatives?"}},
        {{"name": "Pricing Strategy Visibility", "score": <0-100>, "max_score": 100, "weight": 1.0, "notes": "Is pricing transparent and competitively positioned?"}},
        {{"name": "Social Proof vs Competitors", "score": <0-100>, "max_score": 100, "weight": 1.0, "notes": "How does their proof stack (logos, case studies, metrics) compare?"}},
        {{"name": "Content & Thought Leadership", "score": <0-100>, "max_score": 100, "weight": 0.8, "notes": "Who owns the conversation in this space?"}}
    ],
    "competitors": [
        {{
            "name": "Real Competitor Name",
            "url": "competitor-url.com",
            "positioning": "their actual positioning statement or H1",
            "key_differentiator": "what makes them unique vs {company_name}",
            "target_audience": "who they primarily serve",
            "strengths_vs_target": ["specific areas where they're stronger"],
            "weaknesses_vs_target": ["specific areas where {company_name} is stronger"],
            "market_overlap": "High|Medium|Low",
            "threat_level": "High|Medium|Low",
            "messaging_comparison": "how their messaging compares to {company_name}'s"
        }}
    ],
    "positioning_map": {{
        "x_axis": {{"label": "descriptive axis label (e.g. Enterprise ←→ SMB)", "target_position": 0.5}},
        "y_axis": {{"label": "descriptive axis label (e.g. Platform ←→ Point Solution)", "target_position": 0.5}},
        "competitors": [{{"name": "Competitor Name", "x": 0.5, "y": 0.5}}]
    }},
    "feature_comparison": {{
        "categories": ["Capability 1", "Capability 2", "Capability 3", "Capability 4", "Capability 5"],
        "target": {{"Capability 1": true, "Capability 2": true}},
        "competitors": {{
            "Competitor Name": {{"Capability 1": true, "Capability 2": false}}
        }}
    }},
    "market_gaps": ["specific opportunities not well-served by any competitor"],
    "differentiation_opportunities": ["concrete ways to differentiate, with rationale"],
    "win_loss_indicators": {{
        "likely_winning": ["segments or scenarios where {company_name} wins"],
        "likely_losing": ["segments or scenarios where {company_name} loses"],
        "most_contested": ["segments where competition is fiercest"]
    }},
    "strengths": ["3-5 competitive strengths with specific evidence from the website"],
    "weaknesses": ["3-5 competitive weaknesses with business impact estimates"],
    "recommendations": [
        {{
            "issue": "specific competitive challenge with evidence",
            "recommendation": "strategic response with concrete actions",
            "business_impact": "estimated effect on win rates, pipeline, or market share",
            "current_state": "current competitive position",
            "best_practice": "named example of a company handling this well",
            "before_example": "current positioning/messaging that's weak",
            "after_example": "suggested positioning/messaging improvement",
            "impact": "High|Medium|Low",
            "effort": "High|Medium|Low",
            "implementation_steps": ["step 1", "step 2", "step 3"],
            "success_metrics": ["metric to track improvement"],
            "timeline": "timeframe"
        }}
    ],
    "analysis_summary": "3-4 paragraph strategic competitive brief written for a CEO. Frame the competitive landscape, identify where the company is strongest and most vulnerable, and explain what it means for their GTM strategy. This should read like a board-level briefing."
}}

Generate 5-8 specific, actionable competitive recommendations with concrete positioning improvements."""


class CompetitorAgent(BaseAgent):
    agent_name = "competitor"
    agent_display_name = "Competitor Intelligence"
    dependencies = ["web_scraper"]

    async def run(self) -> dict[str, Any]:
        await self.update_progress(10, "Gathering competitive context")

        content = self.get_all_pages_content(max_chars=15000)

        # Use company profile if available
        company_profile = ""
        cp = self.context.get_analysis("company_research")
        if cp and cp.get("status") == "completed":
            company_profile = json.dumps(cp.get("result_data", {}), indent=2)[:5000]

        await self.update_progress(40, "Building competitive analysis prompt")

        prompt = COMPETITOR_PROMPT.format(
            company_url=self.context.company_url,
            company_name=self.context.company_name or "Unknown",
            company_profile=company_profile or "Not available yet.",
            content=content,
        )

        await self.update_progress(45, "Sending to AI for competitive analysis")

        try:
            response = await self.call_llm_json(prompt, system=COMPETITOR_SYSTEM)

            await self.update_progress(70, "Parsing AI competitive response")
            result = self.parse_json(response)

            if not result:
                logger.error(f"Competitor JSON parse failed. Response preview: {response[:500]}")
                self._last_error = f"JSON parse failed. Response starts: {response[:200]}"
                return self._fallback_result()

            # Store competitors in context for other agents
            self.context.competitors = result.get("competitors", [])

            await self.update_progress(85, "Compiling competitive report")

            return {
                "score": result.get("overall_score", 50),
                "grade": None,
                "analysis_text": result.get("analysis_summary", ""),
                "recommendations": result.get("recommendations", []),
                "result_data": {
                    "score_items": result.get("score_items", []),
                    "competitors": result.get("competitors", []),
                    "positioning_map": result.get("positioning_map", {}),
                    "feature_comparison": result.get("feature_comparison", {}),
                    "market_gaps": result.get("market_gaps", []),
                    "differentiation_opportunities": result.get(
                        "differentiation_opportunities", []
                    ),
                    "win_loss_indicators": result.get("win_loss_indicators", {}),
                    "strengths": result.get("strengths", []),
                    "weaknesses": result.get("weaknesses", []),
                    "recommendations": result.get("recommendations", []),
                },
            }
        except Exception as e:
            logger.error(f"Competitor analysis failed: {e}")
            return self._fallback_result()

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
            "analysis_text": "Competitive analysis incomplete — LLM analysis unavailable.",
            "recommendations": [],
            "result_data": {
                "fallback": True,
                "competitors": [],
                "strengths": [],
                "weaknesses": [],
            },
        }

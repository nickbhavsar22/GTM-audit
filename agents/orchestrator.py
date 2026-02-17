"""Project Lead orchestrator — spawns and monitors all specialist agents."""

import asyncio
import logging
from typing import Any, Callable, Optional

from agents.base_agent import BaseAgent
from agents.context_store import ContextStore
from agents.message_bus import MessageBus
from config.constants import QUICK_AUDIT_AGENTS

logger = logging.getLogger(__name__)


class ProjectLead:
    """Orchestrator that manages the audit pipeline.

    Registers all specialist agents, resolves dependencies,
    and executes them in parallel phases.
    """

    def __init__(
        self,
        context: ContextStore,
        message_bus: MessageBus,
        llm_client: Optional[Any] = None,
        db_session: Optional[Any] = None,
        progress_callback: Optional[Callable] = None,
    ):
        self.context = context
        self.bus = message_bus
        self.llm = llm_client
        self.db = db_session
        self.progress_callback = progress_callback
        self._agents: dict[str, BaseAgent] = {}

    def register_agent(self, agent: BaseAgent) -> None:
        self._agents[agent.agent_name] = agent

    def _get_agent_classes(self) -> list[type]:
        """Import and return all agent classes. Handles missing implementations gracefully."""
        classes = []

        # Phase 2 agents (always available after Phase 2)
        try:
            from agents.web_scraper_agent import WebScraperAgent
            classes.append(WebScraperAgent)
        except ImportError:
            logger.warning("WebScraperAgent not implemented yet")

        # Phase 1.5: Screenshot capture via Chrome DevTools MCP
        try:
            from agents.screenshot_agent import ScreenshotAgent
            classes.append(ScreenshotAgent)
        except ImportError:
            logger.debug("ScreenshotAgent not available")

        try:
            from agents.company_research_agent import CompanyResearchAgent
            classes.append(CompanyResearchAgent)
        except ImportError:
            logger.warning("CompanyResearchAgent not implemented yet")

        # Phase 3 agents
        try:
            from agents.seo_agent import SEOAgent
            classes.append(SEOAgent)
        except ImportError:
            logger.debug("SEOAgent not implemented yet")

        try:
            from agents.messaging_agent import MessagingAgent
            classes.append(MessagingAgent)
        except ImportError:
            logger.debug("MessagingAgent not implemented yet")

        try:
            from agents.visual_design_agent import VisualDesignAgent
            classes.append(VisualDesignAgent)
        except ImportError:
            logger.debug("VisualDesignAgent not implemented yet")

        try:
            from agents.competitor_agent import CompetitorAgent
            classes.append(CompetitorAgent)
        except ImportError:
            logger.debug("CompetitorAgent not implemented yet")

        # Phase 4 agents
        try:
            from agents.review_sentiment_agent import ReviewSentimentAgent
            classes.append(ReviewSentimentAgent)
        except ImportError:
            logger.debug("ReviewSentimentAgent not implemented yet")

        try:
            from agents.conversion_agent import ConversionAgent
            classes.append(ConversionAgent)
        except ImportError:
            logger.debug("ConversionAgent not implemented yet")

        try:
            from agents.social_agent import SocialAgent
            classes.append(SocialAgent)
        except ImportError:
            logger.debug("SocialAgent not implemented yet")

        try:
            from agents.icp_agent import ICPAgent
            classes.append(ICPAgent)
        except ImportError:
            logger.debug("ICPAgent not implemented yet")

        # Report agent (always last)
        try:
            from agents.report_agent import ReportAgent
            classes.append(ReportAgent)
        except ImportError:
            logger.warning("ReportAgent not implemented yet")

        return classes

    def register_all_agents(self) -> None:
        """Register all available specialist agents."""
        is_quick = self.context.audit_type == "quick"
        agent_classes = self._get_agent_classes()

        for cls in agent_classes:
            agent = cls(
                context=self.context,
                message_bus=self.bus,
                llm_client=self.llm,
                db_session=self.db,
            )
            # Skip agents not needed for quick audits
            if is_quick and agent.agent_name not in QUICK_AUDIT_AGENTS:
                continue
            self.register_agent(agent)

        logger.info(
            f"Registered {len(self._agents)} agents: "
            f"{list(self._agents.keys())}"
        )

    async def run_phase(self, phase_name: str, agent_names: list[str]) -> None:
        """Run a batch of agents in parallel."""
        tasks = []
        for name in agent_names:
            agent = self._agents.get(name)
            if agent and agent.can_run():
                logger.info(f"[{phase_name}] Starting agent: {name}")
                tasks.append(agent.execute())
            elif agent and not agent.can_run():
                logger.warning(
                    f"[{phase_name}] Skipping {name}: dependencies not met"
                )

        if tasks:
            logger.info(
                f"[{phase_name}] Running {len(tasks)} agents in parallel"
            )
            await asyncio.gather(*tasks, return_exceptions=True)

    async def run_audit(self) -> None:
        """Execute the full audit pipeline in dependency-ordered phases."""
        self.register_all_agents()
        registered = set(self._agents.keys())

        logger.info(
            f"Starting {'quick' if self.context.audit_type == 'quick' else 'full'} "
            f"audit for {self.context.company_url}"
        )

        # Phase 1: Web scraping (no dependencies)
        phase1 = [n for n in ["web_scraper"] if n in registered]
        if phase1:
            await self.run_phase("Crawling", phase1)

        # Phase 1.5: Screenshot capture (depends on web_scraper)
        phase1_5 = [n for n in ["screenshot"] if n in registered]
        if phase1_5:
            await self.run_phase("Screenshots", phase1_5)

        # Phase 2: Company research (depends on web_scraper)
        phase2 = [n for n in ["company_research"] if n in registered]
        if phase2:
            await self.run_phase("Research", phase2)

        # Phase 3: Parallel analysis (depends on web_scraper)
        phase3 = [
            n
            for n in [
                "competitor",
                "review_sentiment",
                "seo",
                "messaging",
                "visual_design",
                "conversion",
                "social",
            ]
            if n in registered
        ]
        if phase3:
            await self.run_phase("Analysis", phase3)

        # Phase 4: ICP (depends on web_scraper + company_research)
        phase4 = [n for n in ["icp"] if n in registered]
        if phase4:
            await self.run_phase("Segmentation", phase4)

        # Phase 5: Report synthesis (depends on all above)
        phase5 = [n for n in ["report"] if n in registered]
        if phase5:
            await self.run_phase("Reporting", phase5)

        logger.info("Audit pipeline complete")

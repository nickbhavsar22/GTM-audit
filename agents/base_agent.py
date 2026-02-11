"""Abstract base class for all GTM audit agents."""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

from agents.context_store import ContextStore
from agents.message_bus import AgentMessage, MessageBus, MessageType

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Abstract base class for all GTM audit specialist agents.

    Subclasses must implement:
      - agent_name: str class attribute
      - agent_display_name: str class attribute
      - run() async method containing the analysis logic

    Optional overrides:
      - dependencies: list of agent_names that must complete first
      - max_retries: number of retry attempts on failure
    """

    agent_name: str = "base"
    agent_display_name: str = "Base Agent"
    dependencies: list[str] = []
    max_retries: int = 3
    retry_delay: float = 2.0  # exponential backoff base (seconds)

    def __init__(
        self,
        context: ContextStore,
        message_bus: MessageBus,
        llm_client: Optional[Any] = None,
        db_session: Optional[Any] = None,
    ):
        self.context = context
        self.bus = message_bus
        self.llm = llm_client
        self.db = db_session
        self._progress: int = 0
        self._current_task: str = ""
        self._status: str = "pending"

    # --- Progress Tracking ---

    async def update_progress(self, pct: int, task: str = "") -> None:
        """Publish a progress update via the message bus and persist to DB."""
        self._progress = min(pct, 100)
        self._current_task = task or self._current_task

        await self.bus.publish(
            AgentMessage(
                sender=self.agent_name,
                message_type=MessageType.PROGRESS_UPDATE,
                data={"progress": self._progress, "task": self._current_task},
            )
        )

        # Persist to database
        if self.db:
            self._persist_progress()

    def _persist_progress(self) -> None:
        """Write current progress to the AgentResult row."""
        try:
            from backend.models.agent_result import AgentResult

            result = (
                self.db.query(AgentResult)
                .filter_by(
                    audit_id=self.context.audit_id,
                    agent_name=self.agent_name,
                )
                .first()
            )
            if result:
                result.progress_pct = self._progress
                result.current_task = self._current_task
                result.status = self._status
                self.db.commit()
        except Exception as e:
            logger.warning(f"[{self.agent_name}] Failed to persist progress: {e}")

    def _persist_result(self, result_data: dict) -> None:
        """Write final results to the AgentResult row."""
        try:
            from backend.models.agent_result import AgentResult
            from datetime import datetime

            result = (
                self.db.query(AgentResult)
                .filter_by(
                    audit_id=self.context.audit_id,
                    agent_name=self.agent_name,
                )
                .first()
            )
            if result:
                result.status = self._status
                result.progress_pct = 100 if self._status == "completed" else self._progress
                result.score = result_data.get("score")
                result.grade = result_data.get("grade")
                result.result_data = result_data.get("result_data")
                result.analysis_text = result_data.get("analysis_text")
                result.recommendations = result_data.get("recommendations")
                result.completed_at = datetime.utcnow()
                result.error_message = result_data.get("error")
                self.db.commit()
        except Exception as e:
            logger.warning(f"[{self.agent_name}] Failed to persist result: {e}")

    # --- Dependency Checking ---

    def can_run(self) -> bool:
        """Check if all dependency agents have completed."""
        for dep in self.dependencies:
            analysis = self.context.get_analysis(dep)
            if not analysis or analysis.get("status") != "completed":
                return False
        return True

    # --- Core Execution ---

    @abstractmethod
    async def run(self) -> dict[str, Any]:
        """Execute the agent's analysis. Subclasses must implement this.

        Returns a dict with at minimum:
          - score: float (0-100)
          - grade: str (e.g., "B+")
          - analysis_text: str
          - recommendations: list[dict]
          - result_data: dict (full structured results)
        """
        ...

    async def execute(self) -> dict[str, Any]:
        """Main entry point with retry logic, error handling, and progress tracking."""
        self._status = "running"
        from datetime import datetime

        if self.db:
            from backend.models.agent_result import AgentResult

            result = (
                self.db.query(AgentResult)
                .filter_by(
                    audit_id=self.context.audit_id,
                    agent_name=self.agent_name,
                )
                .first()
            )
            if result:
                result.started_at = datetime.utcnow()
                result.status = "running"
                self.db.commit()

        await self.update_progress(0, f"Starting {self.agent_display_name}")

        for attempt in range(1, self.max_retries + 1):
            try:
                result = await self.run()

                self._status = "completed"
                await self.update_progress(100, "Complete")

                output = {
                    "status": "completed",
                    **result,
                }
                await self.context.set_analysis(self.agent_name, output)
                self._persist_result(output)

                await self.bus.publish(
                    AgentMessage(
                        sender=self.agent_name,
                        message_type=MessageType.TASK_COMPLETED,
                        data=output,
                    )
                )
                logger.info(f"[{self.agent_name}] Completed successfully")
                return output

            except Exception as e:
                logger.error(
                    f"[{self.agent_name}] Attempt {attempt}/{self.max_retries} "
                    f"failed: {e}"
                )
                if attempt < self.max_retries:
                    delay = self.retry_delay * (2 ** (attempt - 1))
                    await asyncio.sleep(delay)
                else:
                    self._status = "failed"
                    error_result = {
                        "status": "failed",
                        "error": str(e),
                    }
                    await self.context.set_analysis(self.agent_name, error_result)
                    self._persist_result(error_result)

                    await self.bus.publish(
                        AgentMessage(
                            sender=self.agent_name,
                            message_type=MessageType.TASK_FAILED,
                            data=error_result,
                        )
                    )
                    logger.error(f"[{self.agent_name}] Failed after {self.max_retries} attempts")
                    return error_result

    # --- Helper Methods ---

    def get_all_pages_content(self, max_chars: int = 25000) -> str:
        """Aggregate text content from all crawled pages for LLM prompts."""
        return self.context.get_all_text(max_chars)

    async def call_llm(self, prompt: str, system: str = "") -> str:
        """Call the Claude API with the given prompt. Returns response text."""
        if not self.llm:
            raise RuntimeError(f"[{self.agent_name}] No LLM client configured")
        return await self.llm.complete(prompt, system=system)

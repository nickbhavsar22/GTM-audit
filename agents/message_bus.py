"""In-process asyncio message bus for agent communication."""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Awaitable, Callable

logger = logging.getLogger(__name__)


class MessageType(str, Enum):
    PROGRESS_UPDATE = "progress_update"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    DATA_AVAILABLE = "data_available"


@dataclass
class AgentMessage:
    sender: str
    message_type: MessageType
    data: dict[str, Any]
    timestamp: str = field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )


Callback = Callable[[AgentMessage], Awaitable[None]]


class MessageBus:
    """Asyncio-based in-process message bus for agent communication.

    Supports pub/sub pattern: agents subscribe to message types
    and publish messages that get dispatched to all subscribers.
    """

    def __init__(self):
        self._subscribers: dict[str, list[Callback]] = {}
        self._history: list[AgentMessage] = []

    def subscribe(self, message_type: str, callback: Callback) -> None:
        self._subscribers.setdefault(message_type, []).append(callback)

    async def publish(self, message: AgentMessage) -> None:
        self._history.append(message)
        callbacks = self._subscribers.get(message.message_type.value, [])
        if callbacks:
            results = await asyncio.gather(
                *[cb(message) for cb in callbacks],
                return_exceptions=True,
            )
            for r in results:
                if isinstance(r, Exception):
                    logger.warning(
                        f"Message bus callback error for {message.message_type}: {r}"
                    )

    def get_history(
        self, sender: str | None = None, message_type: str | None = None
    ) -> list[AgentMessage]:
        messages = self._history
        if sender:
            messages = [m for m in messages if m.sender == sender]
        if message_type:
            messages = [m for m in messages if m.message_type.value == message_type]
        return messages

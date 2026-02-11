"""WebSocket progress broadcasting service."""

import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ProgressService:
    """Manages WebSocket connections and broadcasts agent progress."""

    _connections: dict[str, list[WebSocket]] = {}

    @classmethod
    def register(cls, audit_id: str, ws: WebSocket) -> None:
        cls._connections.setdefault(audit_id, []).append(ws)

    @classmethod
    def unregister(cls, audit_id: str, ws: WebSocket) -> None:
        if audit_id in cls._connections:
            try:
                cls._connections[audit_id].remove(ws)
            except ValueError:
                pass
            if not cls._connections[audit_id]:
                del cls._connections[audit_id]

    @classmethod
    async def broadcast(cls, audit_id: str, data: dict[str, Any]) -> None:
        """Send progress update to all connected clients for this audit."""
        connections = cls._connections.get(audit_id, [])
        closed = []
        for ws in connections:
            try:
                await ws.send_json(data)
            except Exception:
                closed.append(ws)

        for ws in closed:
            cls.unregister(audit_id, ws)

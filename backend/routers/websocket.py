"""WebSocket endpoint for real-time audit progress."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.services.progress_service import ProgressService

router = APIRouter()


@router.websocket("/ws/audits/{audit_id}/progress")
async def audit_progress(websocket: WebSocket, audit_id: str):
    """WebSocket endpoint for streaming audit progress updates."""
    await websocket.accept()
    ProgressService.register(audit_id, websocket)
    try:
        while True:
            # Keep connection alive; server pushes updates
            await websocket.receive_text()
    except WebSocketDisconnect:
        ProgressService.unregister(audit_id, websocket)

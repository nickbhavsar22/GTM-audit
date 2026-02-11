"""Pydantic schemas for agent status."""

from typing import Optional

from pydantic import BaseModel


class AgentProgressUpdate(BaseModel):
    agent_name: str
    progress_pct: int
    current_task: str = ""
    status: str = "running"

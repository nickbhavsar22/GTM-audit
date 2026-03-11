"""Thin HTTP client for frontend → backend API calls.

All audit execution happens in the backend (uvicorn) process.
The frontend (Streamlit) is a pure UI that communicates via HTTP.
"""

import logging
from typing import Any, Optional

import requests

from config.settings import get_settings

logger = logging.getLogger(__name__)

_TIMEOUT = 10  # seconds for non-audit API calls


def _backend_url() -> str:
    settings = get_settings()
    return f"http://{settings.backend_host}:{settings.backend_port}"


def create_audit(company_url: str, audit_type: str) -> dict[str, Any]:
    """POST /api/audits/create — returns the new audit record."""
    resp = requests.post(
        f"{_backend_url()}/api/audits/create",
        json={"company_url": company_url, "audit_type": audit_type},
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def get_audit_status(audit_id: str) -> dict[str, Any]:
    """GET /api/audits/{id}/status — returns audit + agent statuses."""
    resp = requests.get(
        f"{_backend_url()}/api/audits/{audit_id}/status",
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def get_audit_history() -> list[dict[str, Any]]:
    """GET /api/audits/history — returns list of all audits."""
    resp = requests.get(
        f"{_backend_url()}/api/audits/history",
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def delete_audit(audit_id: str) -> bool:
    """DELETE /api/audits/{id} — returns True on success."""
    resp = requests.delete(
        f"{_backend_url()}/api/audits/{audit_id}",
        timeout=_TIMEOUT,
    )
    return resp.status_code == 200


def get_report(audit_id: str) -> Optional[dict[str, Any]]:
    """GET /api/reports/{id}/report — returns report data or None."""
    resp = requests.get(
        f"{_backend_url()}/api/reports/{audit_id}/report",
        timeout=30,  # reports can be large
    )
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json()

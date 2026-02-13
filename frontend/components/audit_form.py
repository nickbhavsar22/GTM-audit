"""Audit submission form component."""

import asyncio
import logging
import threading
import traceback

import ipaddress
import socket

import streamlit as st
from urllib.parse import urlparse

from backend.models.base import SessionLocal, init_db
from backend.services.audit_service import AuditService

logger = logging.getLogger(__name__)

# Blocked hostnames for SSRF protection
_BLOCKED_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "[::1]", "metadata.google.internal"}


def validate_url(url: str) -> bool:
    """Validate URL format and reject SSRF targets (private IPs, localhost, metadata)."""
    try:
        result = urlparse(url)
        if not all([result.scheme in ("http", "https"), result.netloc]):
            return False
        hostname = result.hostname or ""
        if hostname.lower() in _BLOCKED_HOSTS:
            return False
        # Reject private/reserved IP addresses
        try:
            addr = ipaddress.ip_address(hostname)
            if addr.is_private or addr.is_loopback or addr.is_reserved or addr.is_link_local:
                return False
        except ValueError:
            pass  # Not an IP literal — that's fine (it's a domain name)
        return True
    except Exception:
        return False


def _run_audit_background(audit_id: str) -> None:
    """Run the audit pipeline in a background thread."""
    db = SessionLocal()
    try:
        service = AuditService(db)
        asyncio.run(service.run_audit_async(audit_id))
    except Exception as e:
        logger.exception(f"Background audit {audit_id} failed: {e}")
        # Persist the error to the DB so the UI can show it
        try:
            from backend.models.audit import Audit, AuditStatus
            audit = db.query(Audit).filter(Audit.id == audit_id).first()
            if audit and audit.status != AuditStatus.COMPLETED:
                audit.status = AuditStatus.FAILED
                audit.error_message = f"{type(e).__name__}: {e}\n{traceback.format_exc()[-500:]}"
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


def _show_llm_status() -> None:
    """Show a quick LLM connectivity status check."""
    from config.settings import get_settings
    settings = get_settings()

    if not settings.anthropic_api_key:
        st.error("ANTHROPIC_API_KEY is not configured. Audits will produce fallback data only.")
        return

    # Show model info
    st.caption(f"LLM: {settings.llm_model}")

    # Quick connectivity test (cached to avoid repeated calls)
    if "llm_status" not in st.session_state:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
            resp = client.messages.create(
                model=settings.llm_model,
                max_tokens=10,
                messages=[{"role": "user", "content": "Say OK"}],
            )
            st.session_state["llm_status"] = "ok"
            st.session_state["llm_status_msg"] = resp.content[0].text
        except Exception as e:
            st.session_state["llm_status"] = "error"
            st.session_state["llm_status_msg"] = f"{type(e).__name__}: {e}"

    if st.session_state.get("llm_status") == "ok":
        st.success(f"Claude API connected ({st.session_state['llm_status_msg'].strip()})")
    else:
        st.error(f"Claude API error: {st.session_state.get('llm_status_msg', 'Unknown')}")


def render_audit_form() -> None:
    """Render the audit submission form."""
    st.subheader("Start a New Audit")

    # LLM connectivity check
    _show_llm_status()

    with st.form("audit_form"):
        company_url = st.text_input(
            "Company Website URL",
            placeholder="https://example.com",
            help="Enter the main website URL of the company to audit.",
        )

        audit_type = st.radio(
            "Audit Type",
            options=["Full Audit", "Quick Audit"],
            help="Full audit: 30-45 min, 50+ page report. Quick audit: 10-15 min, 5-page summary.",
            horizontal=True,
        )

        uploaded_files = st.file_uploader(
            "Optional: Upload marketing materials",
            accept_multiple_files=True,
            type=["pdf", "docx", "txt", "png", "jpg"],
            help="Upload any additional materials (pricing docs, marketing collateral, etc.)",
        )

        submitted = st.form_submit_button(
            "Start Audit",
            type="primary",
            use_container_width=True,
        )

        if submitted:
            if not company_url:
                st.error("Please enter a company URL.")
                return

            if not validate_url(company_url):
                st.error("Please enter a valid URL (e.g., https://example.com)")
                return

            audit_type_value = "full" if "Full" in audit_type else "quick"

            try:
                init_db()
                db = SessionLocal()
                try:
                    service = AuditService(db)
                    audit = service.create_audit(company_url, audit_type_value)
                    audit_id = audit.id

                    st.session_state["active_audit_id"] = audit_id
                    st.session_state["active_audit_url"] = company_url

                    # Launch the audit pipeline in a background thread
                    thread = threading.Thread(
                        target=_run_audit_background,
                        args=(audit_id,),
                        daemon=True,
                    )
                    thread.start()

                    st.success(f"Audit started! ID: {audit_id}")
                    st.rerun()
                finally:
                    db.close()
            except Exception as e:
                st.error(f"Failed to start audit: {e}")

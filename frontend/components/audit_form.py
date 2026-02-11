"""Audit submission form component."""

import asyncio
import threading

import streamlit as st
from urllib.parse import urlparse

from backend.models.base import SessionLocal, init_db
from backend.services.audit_service import AuditService


def validate_url(url: str) -> bool:
    """Basic URL validation."""
    try:
        result = urlparse(url)
        return all([result.scheme in ("http", "https"), result.netloc])
    except Exception:
        return False


def _run_audit_background(audit_id: str) -> None:
    """Run the audit pipeline in a background thread."""
    service = AuditService(SessionLocal())
    try:
        asyncio.run(service.run_audit_async(audit_id))
    except Exception:
        pass  # Errors are persisted to DB by run_audit_async


def render_audit_form() -> None:
    """Render the audit submission form."""
    st.subheader("Start a New Audit")

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

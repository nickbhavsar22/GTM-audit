"""Interactive report viewer component with download options."""

import json

import streamlit as st

from backend.models.base import SessionLocal
from backend.services.audit_service import AuditService
from backend.services.report_service import ReportService


def render_report_viewer(audit_id: str) -> None:
    """Display the HTML report with download buttons."""
    db = SessionLocal()
    try:
        service = ReportService(db)
        report = service.get_report(audit_id)

        if not report:
            audit_service = AuditService(db)
            audit = audit_service.get_audit(audit_id)
            if not audit:
                st.error("Audit not found.")
            elif audit.status.value == "running":
                st.warning("Report not yet available. The audit is still in progress.")
            elif audit.status.value in ("completed", "failed"):
                msg = "Report generation failed."
                if audit.error_message:
                    msg += f" Error: {audit.error_message}"
                msg += " Please try running the audit again."
                st.error(msg)
            else:
                st.warning("Report not yet available.")
            return
    finally:
        db.close()

    html_content = report.html_content or ""
    markdown_content = report.markdown_content or ""
    metadata = {}
    if report.report_metadata:
        metadata = report.report_metadata if isinstance(report.report_metadata, dict) else json.loads(report.report_metadata)
    share_token = report.share_token or ""

    # Report header
    st.subheader("Audit Report")
    if metadata:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Overall Score", f"{metadata.get('overall_score', 0):.0f}/100")
        with col2:
            st.metric("Grade", metadata.get("overall_grade", "N/A"))
        with col3:
            st.metric("Recommendations", metadata.get("recommendations", 0))

    st.markdown("---")

    # Download buttons
    col1, col2, col3 = st.columns(3)
    with col1:
        if html_content:
            st.download_button(
                "Download HTML",
                html_content,
                file_name="gtm_audit_report.html",
                mime="text/html",
            )
    with col2:
        if markdown_content:
            st.download_button(
                "Download Markdown",
                markdown_content,
                file_name="gtm_audit_report.md",
                mime="text/markdown",
            )
    with col3:
        st.button("Generate PDF", key="gen_pdf", disabled=True, help="Coming soon")

    st.markdown("---")

    # Render HTML report inline
    if html_content:
        st.components.v1.html(html_content, height=2000, scrolling=True)
    else:
        st.info("No report content available.")

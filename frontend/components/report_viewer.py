"""Interactive report viewer component with download options."""

import streamlit as st

from frontend.utils.api_client import delete_audit, get_audit_status, get_report


def render_report_viewer(audit_id: str) -> None:
    """Display the HTML report with download buttons."""
    report_data = get_report(audit_id)

    if not report_data:
        # Report not found — check audit status for a useful message
        try:
            status_data = get_audit_status(audit_id)
            audit_status = status_data.get("status", "unknown")
            if audit_status == "running":
                st.warning("Report not yet available. The audit is still in progress.")
            elif audit_status in ("completed", "failed"):
                msg = "Report generation failed."
                if status_data.get("error_message"):
                    msg += f" Error: {status_data['error_message']}"
                msg += " Please try running the audit again."
                st.error(msg)
            else:
                st.warning("Report not yet available.")
        except Exception:
            st.error("Audit not found. Is the backend running?")
        return

    html_content = report_data.get("html_content") or ""
    markdown_content = report_data.get("markdown_content") or ""
    metadata = report_data.get("report_metadata") or {}
    share_token = report_data.get("share_token") or ""

    # Report header
    st.subheader("Audit Report")
    if metadata:
        col1, col2, col3 = st.columns(3)
        with col1:
            score = metadata.get("overall_score", 0)
            st.metric("Overall Score", f"{score:.0f}/100" if score else "N/A")
        with col2:
            st.metric("Grade", metadata.get("overall_grade", "N/A"))
        with col3:
            st.metric("Recommendations", metadata.get("recommendations", 0))

    st.markdown("---")

    # Download + delete buttons
    col1, col2, col3, col4 = st.columns(4)
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
    with col4:
        if st.button("🗑️ Delete Audit", key="del_report_audit"):
            st.session_state["confirm_delete_report"] = True
            st.rerun()

    # Delete confirmation
    if st.session_state.get("confirm_delete_report"):
        st.warning(
            "**Delete this audit?** This will permanently remove the audit, "
            "report, and all results. This cannot be undone."
        )
        c1, c2, c3 = st.columns([1, 1, 4])
        with c1:
            if st.button("Confirm Delete", key="yes_del_report", type="primary"):
                delete_audit(audit_id)
                st.session_state.pop("confirm_delete_report", None)
                st.session_state.pop("view_audit_id", None)
                st.switch_page("pages/3_Audit_History.py")
        with c2:
            if st.button("Cancel", key="no_del_report"):
                st.session_state.pop("confirm_delete_report", None)
                st.rerun()
        return  # Don't render report while confirming

    st.markdown("---")

    # Render HTML report inline
    if html_content:
        st.components.v1.html(html_content, height=2000, scrolling=True)
    else:
        st.info("No report content available.")

"""Audit history list component."""

import streamlit as st

from backend.models.base import SessionLocal
from backend.services.audit_service import AuditService


def render_audit_history() -> None:
    """Display list of past audits with status and scores."""
    db = SessionLocal()
    try:
        service = AuditService(db)
        audits = service.list_audits()
    finally:
        db.close()

    if not audits:
        st.info("No audits yet. Start your first audit!")
        return

    for audit in audits:
        status = audit.status.value if audit.status else "unknown"
        status_icon = {
            "completed": ":white_check_mark:",
            "running": ":hourglass_flowing_sand:",
            "failed": ":x:",
            "pending": ":clock3:",
        }.get(status, ":question:")

        with st.container():
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
            with col1:
                company = audit.company_name or audit.company_url or ""
                st.markdown(f"**{company}**")
                st.caption(audit.company_url or "")
            with col2:
                st.markdown(f"{status_icon} {status.capitalize()}")
            with col3:
                score = audit.overall_score
                if score is not None:
                    st.metric("Score", f"{score:.0f}")
                else:
                    st.markdown("—")
            with col4:
                audit_id = audit.id
                if status == "completed":
                    if st.button("View Report", key=f"view_{audit_id}"):
                        st.session_state["view_audit_id"] = audit_id
                        st.switch_page("pages/2_View_Reports.py")
                elif status == "running":
                    if st.button("View Progress", key=f"progress_{audit_id}"):
                        st.session_state["active_audit_id"] = audit_id
                        st.switch_page("pages/1_New_Audit.py")

            st.markdown("---")

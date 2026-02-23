"""Audit history list component."""

import streamlit as st

from backend.models.base import SessionLocal
from backend.services.audit_service import AuditService


def _delete_audit(audit_id: str) -> bool:
    """Delete an audit and all associated data. Returns True on success."""
    db = SessionLocal()
    try:
        service = AuditService(db)
        return service.delete_audit(audit_id)
    finally:
        db.close()


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

        audit_id = audit.id
        confirm_key = f"confirm_delete_{audit_id}"

        with st.container():
            # Check if we're showing the delete confirmation for this audit
            if st.session_state.get(confirm_key):
                st.warning(
                    f"**Delete audit for {audit.company_name or audit.company_url}?** "
                    "This will permanently remove the audit, report, and all results."
                )
                c1, c2, c3 = st.columns([1, 1, 4])
                with c1:
                    if st.button("Confirm Delete", key=f"yes_{audit_id}", type="primary"):
                        _delete_audit(audit_id)
                        del st.session_state[confirm_key]
                        st.rerun()
                with c2:
                    if st.button("Cancel", key=f"no_{audit_id}"):
                        del st.session_state[confirm_key]
                        st.rerun()
            else:
                col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 0.5])
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
                    if status == "completed":
                        if st.button("View Report", key=f"view_{audit_id}"):
                            st.session_state["view_audit_id"] = audit_id
                            st.switch_page("pages/2_View_Reports.py")
                    elif status == "running":
                        if st.button("View Progress", key=f"progress_{audit_id}"):
                            st.session_state["active_audit_id"] = audit_id
                            st.switch_page("pages/1_New_Audit.py")
                with col5:
                    if st.button("🗑️", key=f"del_{audit_id}", help="Delete this audit"):
                        st.session_state[confirm_key] = True
                        st.rerun()

            st.markdown("---")

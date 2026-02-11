"""Real-time progress dashboard for agent execution."""

import time

import streamlit as st

from backend.models.base import SessionLocal
from backend.services.audit_service import AuditService
from config.constants import AGENT_DISPLAY_NAMES


def render_progress_dashboard(audit_id: str) -> None:
    """Display progress bars for all agents with auto-refresh."""
    db = SessionLocal()
    try:
        service = AuditService(db)
        try:
            status_data = service.get_status(audit_id)
        except ValueError:
            st.error("Audit not found.")
            return
    finally:
        db.close()

    # Header
    st.subheader(f"Audit: {status_data.company_url}")
    overall_status = status_data.status

    if overall_status == "completed":
        st.success("Audit completed! (v6)")
        # Show any diagnostic info (e.g. LLM async test failures)
        if status_data.error_message:
            st.warning(f"Diagnostic: {status_data.error_message}")
        score = status_data.overall_score
        grade = status_data.overall_grade
        if score is not None:
            col1, col2, col3 = st.columns([1, 1, 2])
            with col1:
                st.metric("Overall Score", f"{score:.0f}/100")
            with col2:
                st.metric("Grade", grade or "N/A")
            with col3:
                st.markdown("")  # spacer
                if st.button("View Full Report", type="primary", use_container_width=True):
                    st.session_state["view_audit_id"] = audit_id
                    st.switch_page("pages/2_View_Reports.py")
        else:
            if st.button("View Report", type="primary"):
                st.session_state["view_audit_id"] = audit_id
                st.switch_page("pages/2_View_Reports.py")

        # Show agent-level detail for completed audits
        _show_agent_details(status_data.agents)
        return

    if overall_status == "failed":
        st.error(f"Audit failed: {status_data.error_message or 'Unknown error'}")
        _show_agent_details(status_data.agents)
        return

    # Agent progress bars
    st.markdown("### Agent Progress")
    agents = status_data.agents or []

    for agent in agents:
        name = agent.agent_name
        display_name = AGENT_DISPLAY_NAMES.get(name, name)
        progress = (agent.progress_pct or 0) / 100.0
        current_task = agent.current_task or "Waiting..."
        agent_status = agent.status or "pending"

        if agent_status == "completed":
            score_str = f" (Score: {agent.score})" if agent.score is not None else ""
            label = f"{display_name}: Complete{score_str}"
        elif agent_status == "failed":
            label = f"{display_name}: Failed"
        elif agent_status == "running":
            label = f"{display_name}: {current_task}"
        else:
            label = f"{display_name}: Waiting..."

        st.progress(progress, text=label)

        # Show errors inline
        if agent_status == "failed" and agent.error_message:
            st.caption(f"Error: {agent.error_message[:200]}")

    # Auto-refresh while running
    if overall_status == "running":
        time.sleep(3)
        st.rerun()


def _show_agent_details(agents) -> None:
    """Show detailed agent results in an expander."""
    if not agents:
        return

    with st.expander("Agent Details", expanded=False):
        for agent in agents:
            display_name = AGENT_DISPLAY_NAMES.get(agent.agent_name, agent.agent_name)
            score_str = f"Score: {agent.score}" if agent.score is not None else "No score"
            grade_str = f" ({agent.grade})" if agent.grade else ""
            status_icon = {"completed": "OK", "failed": "FAIL", "running": "..."}.get(
                agent.status, "?"
            )
            st.markdown(
                f"**{display_name}** — [{status_icon}] {score_str}{grade_str}"
            )
            if agent.error_message:
                st.code(agent.error_message[:300], language=None)

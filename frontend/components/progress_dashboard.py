"""Real-time progress dashboard for agent execution."""

import time
from types import SimpleNamespace

import streamlit as st

from config.constants import AGENT_DISPLAY_NAMES
from frontend.utils.api_client import get_audit_status


def render_progress_dashboard(audit_id: str) -> None:
    """Display progress cards for all agents with auto-refresh."""
    try:
        status_data = get_audit_status(audit_id)
    except Exception as e:
        st.error(f"Failed to fetch audit status: {e}. Is the backend running?")
        return

    # Convert dict to namespace for attribute access
    agents = [SimpleNamespace(**a) for a in status_data.get("agents", [])]

    # Header
    st.subheader(f"Audit: {status_data.get('company_url', '')}")
    overall_status = status_data.get("status", "pending")

    if overall_status == "completed":
        st.success("Audit completed!")
        # Show any diagnostic info (e.g. LLM async test failures)
        if status_data.get("error_message"):
            st.warning(f"Diagnostic: {status_data['error_message']}")
        score = status_data.get("overall_score")
        grade = status_data.get("overall_grade")
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
        _show_agent_details(agents)
        return

    if overall_status == "failed":
        st.error(f"Audit failed: {status_data.get('error_message') or 'Unknown error'}")
        _show_agent_details(agents)
        return

    # --- In-progress: show agent progress cards ---
    # Summary counters
    completed_count = sum(1 for a in agents if (a.status or "pending") == "completed")
    running_count = sum(1 for a in agents if (a.status or "pending") == "running")
    failed_count = sum(1 for a in agents if (a.status or "pending") == "failed")
    pending_count = len(agents) - completed_count - running_count - failed_count

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Completed", f"{completed_count}/{len(agents)}")
    with col2:
        st.metric("Running", str(running_count))
    with col3:
        st.metric("Pending", str(pending_count))
    with col4:
        st.metric("Failed", str(failed_count))

    # Agent progress cards
    st.markdown("### Agent Progress")
    cards_html = ""
    for agent in agents:
        display_name = AGENT_DISPLAY_NAMES.get(agent.agent_name, agent.agent_name)
        cards_html += _render_agent_card(agent, display_name)

    st.markdown(cards_html, unsafe_allow_html=True)

    # Auto-refresh while running
    if overall_status == "running":
        time.sleep(3)
        st.rerun()


def _render_agent_card(agent, display_name: str) -> str:
    """Generate HTML for a single agent progress card."""
    status = agent.status or "pending"
    progress_pct = agent.progress_pct or 0

    badge_text = {
        "pending": "Pending",
        "running": "Running",
        "completed": "Complete",
        "failed": "Failed",
    }.get(status, status.capitalize())

    # Detail line below the progress bar
    if status == "completed":
        parts = []
        if agent.score is not None:
            parts.append(f'<span class="agent-score">{agent.score:.0f}/100</span>')
        if getattr(agent, "grade", None):
            parts.append(f'<span class="agent-score">({agent.grade})</span>')
        detail = " ".join(parts) if parts else "Done"
    elif status == "failed":
        error_msg = (getattr(agent, "error_message", None) or "Unknown error")[:120]
        detail = f'<span style="color:#EF5350">{error_msg}</span>'
    elif status == "running":
        task_text = getattr(agent, "current_task", None) or "Processing..."
        if "AI" in task_text:
            detail = f'{task_text} <span class="elapsed-pulse">\u2014 waiting for response\u2026</span>'
        else:
            detail = task_text
    else:
        detail = "Queued"

    return f"""<div class="agent-progress-card state-{status}">
  <div class="agent-header">
    <span class="agent-name">{display_name}</span>
    <span class="agent-status-badge badge-{status}">{badge_text}</span>
  </div>
  <div class="agent-progress-track">
    <div class="agent-progress-fill fill-{status}" style="width:{progress_pct}%"></div>
  </div>
  <div class="agent-progress-detail">{detail}</div>
</div>
"""


def _show_agent_details(agents) -> None:
    """Show detailed agent results in an expander."""
    if not agents:
        return

    with st.expander("Agent Details", expanded=False):
        for agent in agents:
            display_name = AGENT_DISPLAY_NAMES.get(agent.agent_name, agent.agent_name)
            score_str = f"Score: {agent.score}" if agent.score is not None else "No score"
            grade_str = f" ({agent.grade})" if getattr(agent, "grade", None) else ""
            status_icon = {"completed": "OK", "failed": "FAIL", "running": "..."}.get(
                agent.status, "?"
            )
            st.markdown(
                f"**{display_name}** — [{status_icon}] {score_str}{grade_str}"
            )
            if getattr(agent, "error_message", None):
                st.code(agent.error_message[:300], language=None)

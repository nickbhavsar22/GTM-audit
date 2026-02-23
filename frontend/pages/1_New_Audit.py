"""New Audit page — submit URL and monitor progress."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st

from frontend.components.auth import check_password
from frontend.components.audit_form import render_audit_form
from frontend.components.progress_dashboard import render_progress_dashboard
from frontend.utils.brand_loader import inject_brand_css

st.set_page_config(
    page_title="New Audit - GTM Audit",
    page_icon="\U0001f4ca",
    layout="wide",
)

inject_brand_css()

# Auth gate
if not check_password():
    st.stop()

st.title("New Audit")

# If an audit is active, show progress dashboard
active_audit = st.session_state.get("active_audit_id")
if active_audit:
    render_progress_dashboard(active_audit)

    st.markdown("---")
    if st.button("Start Another Audit"):
        del st.session_state["active_audit_id"]
        st.rerun()
else:
    render_audit_form()

"""View Reports page — browse and download completed audit reports."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st

from frontend.components.auth import check_password
from frontend.components.report_viewer import render_report_viewer
from frontend.utils.brand_loader import inject_brand_css

st.set_page_config(
    page_title="View Reports - GTM Audit",
    page_icon=":material/analytics:",
    layout="wide",
)

inject_brand_css()

if not check_password():
    st.stop()

st.title("View Reports")

audit_id = (
    st.session_state.get("view_audit_id")
    or st.session_state.get("active_audit_id")
)

if audit_id:
    render_report_viewer(audit_id)

    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Start New Audit"):
            st.session_state.pop("view_audit_id", None)
            st.session_state.pop("active_audit_id", None)
            st.switch_page("pages/1_New_Audit.py")
    with col2:
        if st.button("Audit History"):
            st.session_state.pop("view_audit_id", None)
            st.switch_page("pages/3_Audit_History.py")
else:
    st.info("No audit selected. Start a new audit or pick one from history.")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Start New Audit", type="primary"):
            st.switch_page("pages/1_New_Audit.py")
    with col2:
        if st.button("Audit History"):
            st.switch_page("pages/3_Audit_History.py")

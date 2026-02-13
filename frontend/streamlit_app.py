"""GTM Audit Platform — Streamlit main entry point."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from backend.models.base import init_db
from frontend.components.auth import check_password
from frontend.utils.brand_loader import inject_brand_css

# Initialize database tables on startup
init_db()

st.set_page_config(
    page_title="GTM Audit Platform",
    page_icon=":material/analytics:",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_brand_css()

# Warn if API key is missing
from config.settings import get_settings as _get_settings
if not _get_settings().anthropic_api_key:
    st.warning("ANTHROPIC_API_KEY not configured. Audits will produce limited results. Add it in Settings > Secrets on Streamlit Cloud.")

# Auth gate
if not check_password():
    st.stop()

# Sidebar
with st.sidebar:
    _logo_path = Path(__file__).parent / "assets" / "images" / "bgc_logo.png"
    if _logo_path.exists():
        st.image(str(_logo_path), width=200)
    else:
        st.markdown("### Bhavsar Growth Consulting")
    st.caption("GTM Audit Platform  \nv0.1.0")
    st.markdown("---")

    if st.session_state.get("confirm_logout"):
        st.warning("Are you sure?")
        col_y, col_n = st.columns(2)
        with col_y:
            if st.button("Yes, logout", use_container_width=True):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()
        with col_n:
            if st.button("Cancel", use_container_width=True):
                st.session_state.pop("confirm_logout", None)
                st.rerun()
    else:
        if st.button("Logout", use_container_width=True):
            st.session_state["confirm_logout"] = True
            st.rerun()

# Main content
st.title("GTM Audit Platform")
st.markdown(
    """
    Welcome to the **GTM Audit Platform** — an AI-powered marketing audit tool
    for analyzing B2B SaaS companies' go-to-market strategies.

    ### What You Can Do
    - **New Audit** — Submit a company website URL for comprehensive analysis
    - **View Reports** — Browse completed audit reports
    - **Audit History** — Review past audit results

    ### How It Works
    1. Enter a company's website URL
    2. Choose between a Quick Audit (10-15 min) or Full Audit (30-45 min)
    3. Watch 12 AI agents analyze the company in parallel
    4. Receive a comprehensive report with scores, recommendations, and evidence
    """
)

# Quick action
st.markdown("---")
col1, col2 = st.columns(2)
with col1:
    if st.button("Start New Audit", type="primary", use_container_width=True):
        st.switch_page("pages/1_New_Audit.py")

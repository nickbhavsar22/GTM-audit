"""Sidebar navigation component."""

from pathlib import Path

import streamlit as st


def render_sidebar() -> None:
    """Render the sidebar with navigation and status."""
    with st.sidebar:
        _logo_path = Path(__file__).resolve().parent.parent / "assets" / "images" / "bgc_logo.png"
        if _logo_path.exists():
            st.image(str(_logo_path), width=200)
        else:
            st.markdown("### Bhavsar Growth Consulting")
        st.caption("GTM Audit Platform")
        st.markdown("---")

        st.page_link("frontend/streamlit_app.py", label="Home", icon=":material/home:")
        st.page_link("frontend/pages/1_New_Audit.py", label="New Audit", icon=":material/add_circle:")

        st.markdown("---")

        if st.button("Logout", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

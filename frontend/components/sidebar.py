"""Sidebar navigation component."""

import streamlit as st


def render_sidebar() -> None:
    """Render the sidebar with navigation and status."""
    with st.sidebar:
        st.markdown("### GTM Audit")
        st.markdown("---")

        st.page_link("frontend/streamlit_app.py", label="Home", icon=":material/home:")
        st.page_link("frontend/pages/1_New_Audit.py", label="New Audit", icon=":material/add_circle:")

        st.markdown("---")

        if st.button("Logout", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

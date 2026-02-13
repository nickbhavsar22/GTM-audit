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
        st.caption("GTM Audit Platform  \nv0.1.0")
        st.markdown("---")

        st.page_link("frontend/streamlit_app.py", label="Home", icon=":material/home:")
        st.page_link("frontend/pages/1_New_Audit.py", label="New Audit", icon=":material/add_circle:")

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

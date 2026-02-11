"""Password authentication component for Streamlit."""

import streamlit as st

from config.settings import get_settings


def check_password() -> bool:
    """Display login form and validate password. Returns True if authenticated."""
    if st.session_state.get("authenticated"):
        return True

    st.markdown(
        """
        <div style="text-align: center; padding: 2rem 0;">
            <h1>GTM Audit Platform</h1>
            <p style="color: #94A3B8; font-size: 1.1rem;">
                AI-Powered B2B SaaS Marketing Audit
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("login_form"):
        password = st.text_input("Password", type="password", placeholder="Enter password")
        submitted = st.form_submit_button("Login", type="primary", use_container_width=True)

        if submitted:
            if not password:
                st.error("Please enter a password.")
                return False

            settings = get_settings()
            if password == settings.app_password:
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("Invalid password.")

    return False

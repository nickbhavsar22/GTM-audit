"""Password authentication component for Streamlit."""

import base64
from pathlib import Path

import streamlit as st

from config.settings import get_settings


def check_password() -> bool:
    """Display login form and validate password. Returns True if authenticated."""
    if st.session_state.get("authenticated"):
        return True

    logo_path = Path(__file__).resolve().parent.parent / "assets" / "images" / "bgc_logo.png"
    if logo_path.exists():
        logo_b64 = base64.b64encode(logo_path.read_bytes()).decode()
        logo_html = f'<img src="data:image/png;base64,{logo_b64}" style="width: 220px; margin-bottom: 1rem;" alt="Bhavsar Growth Consulting">'
    else:
        logo_html = ""

    st.markdown(
        f"""
        <div style="text-align: center; padding: 2rem 0;">
            {logo_html}
            <h1 style="color: #DCDAD5; font-weight: 700; letter-spacing: -0.01em;">GTM Audit Platform</h1>
            <p style="color: #8A8780; font-size: 1.1rem;">
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

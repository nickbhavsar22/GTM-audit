"""Load and inject brand CSS into Streamlit pages."""

from pathlib import Path

import streamlit as st

_CSS_PATH = Path(__file__).resolve().parent.parent / "assets" / "css" / "brand.css"


def inject_brand_css():
    """Inject the brand CSS and pinned version label into the current Streamlit page."""
    css = _CSS_PATH.read_text(encoding="utf-8")
    from config.settings import get_version
    version_html = f'<div class="sidebar-version">v{get_version()}</div>'
    st.markdown(f"<style>{css}</style>{version_html}", unsafe_allow_html=True)

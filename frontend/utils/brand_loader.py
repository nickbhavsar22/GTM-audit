"""Load and inject brand CSS into Streamlit pages."""

from pathlib import Path

import streamlit as st

_CSS_PATH = Path(__file__).resolve().parent.parent / "assets" / "css" / "brand.css"


def inject_brand_css():
    """Inject the brand CSS into the current Streamlit page."""
    css = _CSS_PATH.read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

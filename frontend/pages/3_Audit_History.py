"""Audit History page — list all past audits."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st

from frontend.components.auth import check_password
from frontend.components.audit_history import render_audit_history
from frontend.utils.brand_loader import inject_brand_css

st.set_page_config(
    page_title="Audit History - GTM Audit",
    page_icon="\U0001f4ca",
    layout="wide",
)

inject_brand_css()

if not check_password():
    st.stop()

st.title("Audit History")
render_audit_history()

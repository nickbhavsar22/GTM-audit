"""New Audit page — submit URL and monitor progress."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st

from frontend.components.auth import check_password
from frontend.components.audit_form import render_audit_form
from frontend.components.progress_dashboard import render_progress_dashboard

st.set_page_config(
    page_title="New Audit - GTM Audit",
    page_icon=":material/analytics:",
    layout="wide",
)

# Auth gate
if not check_password():
    st.stop()

st.title("New Audit")

# Inline LLM diagnostic (temporary)
try:
    from config.settings import get_settings
    _s = get_settings()
    _key_info = f"Key: {'set (...' + _s.anthropic_api_key[-8:] + ')' if _s.anthropic_api_key else 'MISSING'}"
    _model_info = f"Model: {_s.llm_model}"
    st.info(f"Config: {_key_info} | {_model_info}")

    if _s.anthropic_api_key:
        try:
            import anthropic
            _client = anthropic.Anthropic(api_key=_s.anthropic_api_key)
            _resp = _client.messages.create(
                model=_s.llm_model,
                max_tokens=10,
                messages=[{"role": "user", "content": "Say OK"}],
            )
            st.success(f"Claude API OK: {_resp.content[0].text}")
        except Exception as _e:
            st.error(f"Claude API FAILED: {type(_e).__name__}: {_e}")
    else:
        st.error("No API key — audits will use fallback data")
except Exception as _e:
    st.error(f"Config error: {type(_e).__name__}: {_e}")

# If an audit is active, show progress dashboard
active_audit = st.session_state.get("active_audit_id")
if active_audit:
    render_progress_dashboard(active_audit)

    st.markdown("---")
    if st.button("Start Another Audit"):
        del st.session_state["active_audit_id"]
        st.rerun()
else:
    render_audit_form()

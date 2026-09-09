import asyncio
import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.portfolio_service import analyze_portfolio  # noqa: E402

st.set_page_config(page_title="Portfolio", page_icon=":material/inventory_2:", layout="wide")
st.title(":material/inventory_2: Portfolio View")
st.caption(
    "Separate what your brand can confidently promote from competitor-only "
    "opportunities to evaluate."
)


if "portfolio_analysis" not in st.session_state:
    st.session_state.portfolio_analysis = None

if st.button("Analyze portfolio with LLM", type="primary"):
    try:
        with st.spinner("Comparing your portfolio with competitor offerings..."):
            st.session_state.portfolio_analysis = asyncio.run(analyze_portfolio())
    except ValueError as exc:
        st.error(str(exc))

analysis = st.session_state.portfolio_analysis
have_tab, not_have_tab = st.tabs(["Have in portfolio", "Not in our portfolio"])

with have_tab:
    st.subheader("Services supported by your website")
    items = analysis.get("have_in_portfolio", []) if analysis else []
    if not analysis:
        st.info("Click Analyze portfolio with LLM to compare your sources.")
    elif not items:
        st.info("No own services were identified. Scrape your website first.")
    for item in items:
        with st.expander(item.get("service_name", "Unnamed service")):
            st.write(item.get("evidence", "No evidence returned."))
            if item.get("source"):
                st.caption(f"Source: {item['source']}")

with not_have_tab:
    st.subheader("Competitor offerings to evaluate")
    st.caption("These are competitor signals, not approved services or CTAs for your brand.")
    items = analysis.get("not_in_portfolio", []) if analysis else []
    if not analysis:
        st.info("Click Analyze portfolio with LLM to compare your sources.")
    elif not items:
        st.info("No competitor-only offerings were identified.")
    for item in items:
        with st.expander(item.get("service_name", "Unnamed opportunity")):
            if item.get("competitor"):
                st.markdown(f"**Competitor:** {item['competitor']}")
            st.write(item.get("evidence", "No evidence returned."))
            if item.get("opportunity"):
                st.caption(f"Opportunity: {item['opportunity']}")

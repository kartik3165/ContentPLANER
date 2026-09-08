import asyncio
import json
import sys
from datetime import date
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.plan_service import generate_plan  # noqa: E402

st.set_page_config(page_title="Content Plan", layout="wide")
st.title(":material/calendar_month: N-Day Content Plan")

with st.form("plan"):
    n = st.number_input("Number of days", 1, 30, 7)
    start = st.date_input("Start date", value=date.today())
    ok = st.form_submit_button("Generate Plan", type="primary")

if ok:
    try:
        with st.spinner("Generating calendar-aware plan..."):
            plan = asyncio.run(generate_plan(int(n), start))
    except ValueError as exc:
        st.error("The content plan response was incomplete. Please try again.")
        st.caption(str(exc).split("Raw snippet:", maxsplit=1)[0].strip())
        st.stop()
    for d in plan.get("days", []):
        with st.expander(f"Day {d['day']} — {d['date']} — {d['title']}"):
            st.markdown(f"**Format:** {d['format']}")
            st.markdown(f"**Hook:** {d['hook']}")
            st.markdown(f"**Caption:**\n\n{d['caption']}")
            st.markdown(f"**CTA:** {d['cta']}")
    st.download_button(
        "Download JSON",
        json.dumps(plan, indent=2),
        "content_plan.json",
        "application/json",
    )

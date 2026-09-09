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

st.set_page_config(page_title="Content Plan", page_icon=":material/calendar_month:", layout="wide")
st.title(":material/calendar_month: Generate Content Plan")
st.caption(
    "Generate N days of content using your portfolio, competitor services, "
    "and Instagram post patterns."
)

with st.form("content_plan"):
    days = st.number_input("Number of days", min_value=1, max_value=30, value=7)
    start = st.date_input("Start date", value=date.today())
    generate = st.form_submit_button("Generate plan", type="primary")

if generate:
    try:
        with st.spinner("Combining sources and generating your plan..."):
            plan = asyncio.run(generate_plan(int(days), start))
    except ValueError as exc:
        st.error("The model returned an incomplete plan. Please try again.")
        st.caption(str(exc).split("Raw snippet:", maxsplit=1)[0].strip())
        st.stop()
    for day in plan.get("days", []):
        with st.expander(f"Day {day['day']} · {day['date']} · {day['title']}"):
            st.markdown(f"**Format:** {day['format']}")
            st.markdown(f"**Hook:** {day['hook']}")
            st.markdown(f"**Caption:**\n\n{day['caption']}")
            st.markdown(f"**CTA:** {day['cta']}")
            if day.get("festival_tie_in"):
                st.caption(f"Festival tie-in: {day['festival_tie_in']}")
    st.download_button(
        "Download JSON",
        json.dumps(plan, indent=2),
        "content_plan.json",
        "application/json",
    )

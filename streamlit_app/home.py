import asyncio
import sys
from pathlib import Path

import streamlit as st
from sqlalchemy import func
from sqlmodel import select

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.database import async_session_maker  # noqa: E402
from app.models import CrawledSource, InstagramPost, WebsiteDataChunks  # noqa: E402

st.set_page_config(
    page_title="ContentPlan Dashboard", page_icon=":material/dashboard:", layout="wide"
)
st.title(":material/dashboard: ContentPlan")
st.caption("One workspace for source intelligence, portfolio gaps, and content planning.")


async def load_metrics() -> dict[str, int]:
    async with async_session_maker() as session:
        websites = await session.execute(
            select(func.count(CrawledSource.id)).where(CrawledSource.source_type == "website")
        )
        instagram = await session.execute(select(func.count(InstagramPost.id)))
        own_chunks = await session.execute(
            select(func.count(WebsiteDataChunks.id)).where(WebsiteDataChunks.owner == "own")
        )
        competitor_chunks = await session.execute(
            select(func.count(WebsiteDataChunks.id)).where(
                WebsiteDataChunks.owner == "competition"
            )
        )
        return {
            "websites": websites.scalar_one(),
            "instagram": instagram.scalar_one(),
            "own_chunks": own_chunks.scalar_one(),
            "competitor_chunks": competitor_chunks.scalar_one(),
        }


metrics = asyncio.run(load_metrics())
cards = st.columns(4)
cards[0].metric("Websites scraped", metrics["websites"])
cards[1].metric("Instagram posts", metrics["instagram"])
cards[2].metric("Own portfolio content", metrics["own_chunks"])
cards[3].metric("Competitor website content", metrics["competitor_chunks"])

st.divider()
st.subheader("Workflow")
workflow = st.columns(4)
workflow[0].page_link(
    "pages/1_Social_Sources.py", label="1. Social sources", icon=":material/public:"
)
workflow[1].page_link("pages/2_Competitors.py", label="2. Competitors", icon=":material/groups:")
workflow[2].page_link(
    "pages/3_Portfolio.py", label="3. Portfolio", icon=":material/inventory_2:"
)
workflow[3].page_link(
    "pages/4_Content_Plan.py", label="4. Generate plan", icon=":material/calendar_month:"
)

st.info(
    "Scrape your website and Instagram first. Add competitor sources next. "
    "The plan generator combines both datasets and uses competitor services only for comparison."
)

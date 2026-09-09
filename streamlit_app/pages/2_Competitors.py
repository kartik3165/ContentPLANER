import asyncio
import sys
import uuid
from pathlib import Path

import streamlit as st
from sqlmodel import select

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.database import async_session_maker  # noqa: E402
from app.models import Competitor, PostOwnerType  # noqa: E402
from app.services.crawl_instagram import process_instagram_job  # noqa: E402
from app.services.crawl_service import (  # noqa: E402
    normalize_source_url,
    process_crawl_job,
    source_exists,
)
from app.services.job_store import create_job, get_job  # noqa: E402

st.set_page_config(page_title="Competitors", page_icon=":material/groups:", layout="wide")
st.title(":material/groups: Competitors")
st.caption(
    "Add competitor websites and Instagram accounts, then refresh either source independently."
)

with st.form("add_competitor"):
    col_1, col_2 = st.columns(2)
    with col_1:
        website = st.text_input("Competitor website", placeholder="https://competitor.com")
    with col_2:
        instagram = st.text_input("Competitor Instagram", placeholder="competitorhandle")
    submitted = st.form_submit_button("Add competitor", type="primary")

if submitted:
    if not website.strip() and not instagram.strip():
        st.warning("Add a website, an Instagram account, or both.")
    else:
        async def add_competitor():
            async with async_session_maker() as session:
                session.add(
                    Competitor(
                        website_url=website.strip() or None,
                        instagram_handle=instagram.strip().lstrip("@") or None,
                    )
                )
                await session.commit()

        asyncio.run(add_competitor())
        st.success("Competitor added.")
        st.rerun()


async def load_competitors() -> list[Competitor]:
    async with async_session_maker() as session:
        result = await session.execute(select(Competitor).order_by(Competitor.created_at.desc()))
        return list(result.scalars().all())


competitors = asyncio.run(load_competitors())
if not competitors:
    st.info("No competitors added yet.")
    st.stop()

refresh_all = st.checkbox("Allow re-scraping for the next action")


def scrape_website(url: str):
    url = normalize_source_url(url)
    exists = asyncio.run(source_exists(url, "website"))
    if exists and not refresh_all:
        st.error("This website is already saved. Enable re-scraping first.")
        return
    job_id = str(uuid.uuid4())
    create_job(job_id, url)
    try:
        with st.spinner(f"Scraping {url}..."):
            asyncio.run(
                process_crawl_job(job_id, url, 10, "competition", refresh=refresh_all)
            )
    except (RuntimeError, ValueError) as exc:
        st.error(str(exc))
        return
    job = get_job(job_id)
    if job and job.status == "completed":
        st.success(f"Saved {job.chunks_created} competitor website content blocks.")
    else:
        st.error(f"Website scrape failed: {job.status if job else 'unknown'}")


def scrape_instagram(username: str):
    exists = asyncio.run(source_exists(username, "instagram"))
    if exists and not refresh_all:
        st.error("This account is already saved. Enable re-scraping first.")
        return
    job_id = str(uuid.uuid4())
    create_job(job_id, username)
    with st.spinner(f"Scraping @{username}..."):
        asyncio.run(
            process_instagram_job(
                job_id, username, PostOwnerType.COMPETITION, refresh=refresh_all
            )
        )
    job = get_job(job_id)
    if job and job.status == "completed":
        st.success(f"Saved {job.chunks_created} competitor posts.")
    else:
        st.error(f"Instagram scrape failed: {job.status if job else 'unknown'}")


for index, competitor in enumerate(competitors):
    with st.container(border=True):
        st.subheader(f"Competitor {index + 1}")
        st.write(f"Website: `{competitor.website_url or 'not added'}`")
        st.write(f"Instagram: `@{competitor.instagram_handle or 'not added'}`")
        actions = st.columns(2)
        with actions[0]:
            if competitor.website_url and st.button("Scrape website", key=f"web_{competitor.id}"):
                scrape_website(competitor.website_url)
        with actions[1]:
            if competitor.instagram_handle and st.button(
                "Scrape Instagram", key=f"ig_{competitor.id}"
            ):
                scrape_instagram(competitor.instagram_handle)

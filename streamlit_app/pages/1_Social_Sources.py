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
from app.models import CrawledSource, InstagramPost, PostOwnerType  # noqa: E402
from app.services.crawl_instagram import process_instagram_job  # noqa: E402
from app.services.crawl_service import (  # noqa: E402
    normalize_source_url,
    process_crawl_job,
    source_exists,
)
from app.services.job_store import create_job, get_job  # noqa: E402

st.set_page_config(page_title="Social Sources", page_icon=":material/public:", layout="wide")
st.title(":material/public: My Social Sources")
st.caption(
    "Scrape your own website and Instagram account, review the saved data, "
    "and refresh it whenever needed."
)


def run_website_scrape(url: str, limit: int, refresh: bool):
    url = normalize_source_url(url)
    if asyncio.run(source_exists(url, "website")) and not refresh:
        st.error("This website is already saved. Turn on re-scrape to refresh it.")
        return
    job_id = str(uuid.uuid4())
    create_job(job_id, url)
    try:
        with st.spinner("Scraping and indexing your website..."):
            asyncio.run(process_crawl_job(job_id, url, limit, "own", refresh=refresh))
    except (RuntimeError, ValueError) as exc:
        st.error(str(exc))
        return
    job = get_job(job_id)
    if job and job.status == "completed":
        st.success(f"Website refreshed. {job.chunks_created} content blocks indexed.")
    else:
        st.error(f"Website scrape failed: {job.status if job else 'unknown'}")


def run_instagram_scrape(username: str, refresh: bool):
    if asyncio.run(source_exists(username, "instagram")) and not refresh:
        st.error("This Instagram account is already saved. Turn on re-scrape to refresh it.")
        return
    job_id = str(uuid.uuid4())
    create_job(job_id, username)
    with st.spinner("Scraping your latest Instagram posts..."):
        asyncio.run(process_instagram_job(job_id, username, PostOwnerType.OWN, refresh=refresh))
    job = get_job(job_id)
    if job and job.status == "completed":
        st.success(f"Instagram refreshed. {job.chunks_created} posts saved.")
    else:
        st.error(f"Instagram scrape failed: {job.status if job else 'unknown'}")


async def load_website_sources() -> list[CrawledSource]:
    async with async_session_maker() as session:
        result = await session.execute(
            select(CrawledSource)
            .where(CrawledSource.source_type == "website")
            .order_by(CrawledSource.created_at.desc())
        )
        return list(result.scalars().all())


async def load_own_posts() -> list[InstagramPost]:
    async with async_session_maker() as session:
        result = await session.execute(
            select(InstagramPost)
            .where(InstagramPost.post_owner_type == PostOwnerType.OWN)
            .order_by(InstagramPost.engagement_score.desc())
        )
        return list(result.scalars().all())


saved_sources = asyncio.run(load_website_sources())
saved_posts = asyncio.run(load_own_posts())
website_blocks = sum(source.chunks_count for source in saved_sources)
summary_website, summary_instagram = st.columns(2)
summary_website.metric(
    "Website content saved",
    website_blocks,
    help="Total indexed content blocks across your saved websites.",
)
summary_instagram.metric(
    "Instagram posts saved",
    len(saved_posts),
    help="Total posts saved from your own Instagram account.",
)


scrape_tab, details_tab = st.tabs(["Scrape and refresh", "Saved details"])
with scrape_tab:
    left, right = st.columns(2)
    with left:
        st.subheader("Website")
        with st.form("own_website_form"):
            url = st.text_input("Website URL", placeholder="https://yourbrand.com")
            limit = st.slider("Maximum pages", 1, 50, 10)
            refresh = st.checkbox("Re-scrape existing website")
            submit = st.form_submit_button("Scrape website", type="primary")
        if submit:
            if not url.strip():
                st.warning("Enter your website URL.")
            else:
                run_website_scrape(url.strip(), limit, refresh)
    with right:
        st.subheader("Instagram")
        with st.form("own_instagram_form"):
            username = st.text_input("Instagram username", placeholder="yourbrand")
            refresh = st.checkbox("Re-scrape existing account")
            submit = st.form_submit_button("Scrape Instagram", type="primary")
        if submit:
            if not username.strip():
                st.warning("Enter your Instagram username.")
            else:
                run_instagram_scrape(username.strip().lstrip("@"), refresh)

with details_tab:
    sources = saved_sources
    posts = saved_posts
    metric_1, metric_2, metric_3 = st.columns(3)
    metric_1.metric("Saved websites", len(sources))
    metric_2.metric("Instagram posts", len(posts))
    metric_3.metric("Sources ready", len(sources) + (1 if posts else 0))
    if sources:
        st.dataframe(
            [
                {
                    "Website": source.source_url,
                    "Last scraped": source.created_at,
                }
                for source in sources
            ],
            use_container_width=True,
            hide_index=True,
        )
    if posts:
        st.dataframe(
            [
                {
                    "Username": post.owner_username,
                    "Type": post.postType,
                    "Likes": post.likesCount,
                    "Comments": post.commentsCount,
                    "Views": post.videoViewCount,
                    "Engagement score": round(post.engagement_score, 1),
                    "Post": post.postUrl,
                }
                for post in posts
            ],
            use_container_width=True,
            hide_index=True,
            column_config={"Post": st.column_config.LinkColumn("Post")},
        )

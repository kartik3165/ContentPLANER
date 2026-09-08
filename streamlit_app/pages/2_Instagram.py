import asyncio
import uuid

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.models import PostOwnerType
from app.services.crawl_instagram import process_instagram_job
from app.services.crawl_service import source_exists
from app.services.job_store import create_job, get_job

st.set_page_config(page_title="Instagram", layout="wide")
st.title(":material/photo_camera: Instagram Scraper")

with st.form("ig_form"):
    username = st.text_input("Username", placeholder="flyingpandathemepark")
    owner_type = st.selectbox("Owner", ["own", "competition"])
    ok = st.form_submit_button("Scrape", type="primary")

if ok:
    if not username:
        st.warning("Enter a username.")
        st.stop()
    if asyncio.run(source_exists(username, "instagram")):
        st.error(f"Already scraped: {username} — blocked, each account only once.")
        st.stop()
    job_id = str(uuid.uuid4())
    create_job(job_id, username)
    ot = PostOwnerType.COMPETITION if owner_type == "competition" else PostOwnerType.OWN
    with st.spinner("Scraping..."):
        asyncio.run(process_instagram_job(job_id, username, ot))
    job = get_job(job_id)
    if job and job.status == "completed":
        st.success(f"Done! {job.chunks_created} posts stored.")
    elif job and job.status == "already_exists":
        st.error("Already exists — blocked.")
    else:
        st.error(f"Failed: {job.status if job else 'unknown'}")

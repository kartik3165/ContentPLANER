import asyncio
import uuid

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.crawl_service import process_crawl_job, source_exists
from app.services.job_store import create_job, get_job

st.set_page_config(page_title="Crawl Site", layout="wide")
st.title(":material/language: Crawl Own Site")

with st.form("crawl_form"):
    url = st.text_input("Website URL", placeholder="https://example.com")
    owner = st.selectbox("Owner", ["own", "competition"])
    limit = st.slider("Max pages", 1, 50, 10)
    ok = st.form_submit_button("Start Crawl", type="primary")

if ok:
    if not url:
        st.warning("Enter a URL.")
        st.stop()
    if asyncio.run(source_exists(url, "website")):
        st.error(f"Already crawled: {url} — blocked, each site only once.")
        st.stop()
    job_id = str(uuid.uuid4())
    create_job(job_id, url)
    with st.spinner("Crawling..."):
        asyncio.run(process_crawl_job(job_id, url, limit, owner))
    job = get_job(job_id)
    if job and job.status == "completed":
        st.success(f"Done! {job.chunks_created} chunks stored.")
    elif job and job.status == "already_exists":
        st.error("Already exists — blocked.")
    else:
        st.error(f"Failed: {job.status if job else 'unknown'}")

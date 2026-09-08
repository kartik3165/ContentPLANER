import asyncio

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from langchain_aws import BedrockEmbeddings
from sqlmodel import select

from app.database import async_session_maker
from app.models import WebsiteDataChunks, WebsiteDataEmbedding

st.set_page_config(page_title="Search", layout="wide")
st.title(":material/search: Search")

with st.form("s"):
    q = st.text_input("Query", placeholder="What are the services?")
    k = st.slider("Results", 1, 10, 3)
    ok = st.form_submit_button("Search", type="primary")

if ok and q:
    emb = BedrockEmbeddings(
        model_id="amazon.titan-embed-text-v2:0",
        region_name="ap-south-1",
        normalize=True,
    )

    async def run():
        qv = await emb.aembed_query(q)
        dist = WebsiteDataEmbedding.embedding.l2_distance(qv).label("dist")
        async with async_session_maker() as session:
            stmt = (
                select(
                    WebsiteDataChunks.content,
                    WebsiteDataChunks.source_file,
                    WebsiteDataChunks.chunk_index,
                    dist,
                )
                .join(
                    WebsiteDataEmbedding,
                    WebsiteDataEmbedding.chunk_id == WebsiteDataChunks.id,
                )
                .order_by(dist)
                .limit(k)
            )
            return (await session.execute(stmt)).all()

    with st.spinner("Searching..."):
        rows = asyncio.run(run())
    if not rows:
        st.info("No results.")
    for i, (content, src, idx, dist) in enumerate(rows):
        with st.expander(f"Result {i + 1} — {src} #{idx} (dist {dist:.4f})"):
            st.markdown(content)

import asyncio
import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlmodel import select  # noqa: E402, I001

from app.database import async_session_maker  # noqa: E402
from app.models import CrawledSource, WebsiteDataChunks  # noqa: E402


st.set_page_config(page_title="Scraped Website Data", layout="wide")
st.title(":material/description: Scraped Website Data")
st.caption("Browse crawled sources and the text chunks saved for search.")


async def load_sources() -> list[CrawledSource]:
    async with async_session_maker() as session:
        result = await session.execute(
            select(CrawledSource)
            .where(CrawledSource.source_type == "website")
            .order_by(CrawledSource.created_at.desc())
        )
        return list(result.scalars().all())


async def load_chunks(source_url: str) -> list[WebsiteDataChunks]:
    async with async_session_maker() as session:
        result = await session.execute(
            select(WebsiteDataChunks)
            .where(WebsiteDataChunks.source_file == source_url)
            .order_by(WebsiteDataChunks.chunk_index)
        )
        return list(result.scalars().all())


sources = asyncio.run(load_sources())
if not sources:
    st.info("No website data has been scraped yet.")
    st.stop()

st.metric("Crawled websites", len(sources))
source_labels = {
    f"{source.source_url} ({source.chunks_count} chunks)": source.source_url
    for source in sources
}
selected_label = st.selectbox("Website", list(source_labels))
selected_url = source_labels[selected_label]
chunks = asyncio.run(load_chunks(selected_url))

st.subheader(f"{len(chunks)} saved chunks")
st.dataframe(
    [
        {
            "Chunk": chunk.chunk_index,
            "Owner": chunk.owner,
            "Characters": len(chunk.content),
            "Created": chunk.created_at,
        }
        for chunk in chunks
    ],
    use_container_width=True,
    hide_index=True,
)

for chunk in chunks:
    with st.expander(f"Chunk {chunk.chunk_index} · {len(chunk.content):,} characters"):
        st.markdown(chunk.content)
        if chunk.metadata_json:
            st.caption(f"Metadata: {chunk.metadata_json}")

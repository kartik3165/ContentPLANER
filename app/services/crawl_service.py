import json
import re

from firecrawl import AsyncFirecrawl
from langchain_aws import BedrockEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlmodel import select

from app.database import async_session_maker
from app.models import CrawledSource, WebsiteDataChunks, WebsiteDataEmbedding
from app.services.job_store import update_job

embeddings = BedrockEmbeddings(
    model_id="amazon.titan-embed-text-v2:0",
    region_name="ap-south-1",
    normalize=True,
)


async def source_exists(source_url: str, source_type: str = "website") -> bool:
    async with async_session_maker() as session:
        result = await session.execute(
            select(CrawledSource.id).where(
                CrawledSource.source_url == source_url,
                CrawledSource.source_type == source_type,
            )
        )
        return result.scalars().first() is not None


async def record_source(source_url: str, source_type: str, chunks_count: int):
    async with async_session_maker() as session:
        record = CrawledSource(
            source_url=source_url,
            source_type=source_type,
            chunks_count=chunks_count,
        )
        session.add(record)
        await session.commit()


async def crawl_website(url: str, api_key: str, limit: int = 10) -> str:
    crawler = AsyncFirecrawl(api_key=api_key)
    status = await crawler.crawl(
        url=url,
        limit=limit,
        scrape_options={"formats": ["markdown", "html"]},
        poll_interval=2,
        timeout=180,
    )
    if status.status != "completed":
        state = status.status or "unknown"
        raise RuntimeError(f"Website crawl did not complete. Firecrawl status: {state}")
    content_parts = [
        page.markdown or page.html or page.raw_html or page.summary
        for page in (status.data or [])
    ]
    markdown = "\n\n---\n\n".join(content for content in content_parts if content).strip()
    if not markdown:
        raise ValueError(
            f"Website crawl completed but returned no page content "
            f"({status.completed}/{status.total} pages completed)."
        )
    return markdown


def normalize_source_url(source_url: str) -> str:
    value = source_url.strip()
    markdown_link = re.fullmatch(r"\[[^\]]+\]\((https?://[^)]+)\)", value)
    return markdown_link.group(1) if markdown_link else value


async def chunk_markdown(markdown_content: str, source_url: str, owner: str = "own"):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100,
    )
    metadata_type = "competition_site" if owner == "competition" else "own_site"
    docs = splitter.create_documents(
        texts=[markdown_content],
        metadatas=[{"source_url": source_url, "type": metadata_type}],
    )
    for i, doc in enumerate(docs):
        doc.metadata["chunk_id"] = i
    return docs


async def delete_existing_chunks(source_url: str):
    async with async_session_maker() as session:
        result = await session.execute(
            select(WebsiteDataChunks).where(WebsiteDataChunks.source_file == source_url)
        )
        for chunk in result.scalars().all():
            await session.delete(chunk)
        await session.commit()


async def delete_source_record(source_url: str, source_type: str = "website"):
    async with async_session_maker() as session:
        result = await session.execute(
            select(CrawledSource).where(
                CrawledSource.source_url == source_url,
                CrawledSource.source_type == source_type,
            )
        )
        for source in result.scalars().all():
            await session.delete(source)
        await session.commit()


async def store_chunks_and_embeddings(source_url: str, chunks, owner: str = "own"):
    async with async_session_maker() as session:
        for chunk in chunks:
            db_chunk = WebsiteDataChunks(
                source_file=source_url,
                owner=owner,
                chunk_index=chunk.metadata.get("chunk_id", 0),
                content=chunk.page_content,
                metadata_json=json.dumps(chunk.metadata),
            )
            session.add(db_chunk)
            await session.flush()
            embedding_vector = await embeddings.aembed_query(chunk.page_content)
            db_embedding = WebsiteDataEmbedding(
                chunk_id=db_chunk.id,
                embedding=embedding_vector,
                model_id="amazon.titan-embed-text-v2:0",
            )
            session.add(db_embedding)
        await session.commit()
        return len(chunks)


async def process_crawl_job(
    job_id: str, url: str, limit: int, owner: str = "own", refresh: bool = False
):
    from app.settings import get_settings

    settings = get_settings()
    url = normalize_source_url(url)
    try:
        exists = await source_exists(url, "website")
        if exists and not refresh:
            update_job(job_id, status="already_exists", chunks_created=0)
            return
        markdown = await crawl_website(url, settings.firecrawl_api, limit)
        chunks = await chunk_markdown(markdown, url, owner=owner)
        await delete_existing_chunks(url)
        await delete_source_record(url, "website")
        count = await store_chunks_and_embeddings(url, chunks, owner=owner)
        await record_source(url, "website", count)
        update_job(job_id, status="completed", chunks_created=count)
    except Exception:
        update_job(job_id, status="failed")
        raise

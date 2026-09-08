import json

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
    job = await crawler.start_crawl(url, limit=limit)
    status = await crawler.get_crawl_status(job.id)
    markdown_parts = [page.markdown for page in (status.data or []) if page.markdown]
    return "\n\n---\n\n".join(markdown_parts)


async def chunk_markdown(markdown_content: str, source_url: str):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100,
    )
    docs = splitter.create_documents(
        texts=[markdown_content],
        metadatas=[{"source_url": source_url, "type": "own_site"}],
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


async def process_crawl_job(job_id: str, url: str, limit: int, owner: str = "own"):
    from app.settings import get_settings

    settings = get_settings()
    try:
        exists = await source_exists(url, "website")
        if exists:
            update_job(job_id, status="already_exists", chunks_created=0)
            return
        markdown = await crawl_website(url, settings.firecrawl_api, limit)
        chunks = await chunk_markdown(markdown, url)
        await delete_existing_chunks(url)
        count = await store_chunks_and_embeddings(url, chunks, owner=owner)
        await record_source(url, "website", count)
        update_job(job_id, status="completed", chunks_created=count)
    except Exception:
        update_job(job_id, status="failed")
        raise

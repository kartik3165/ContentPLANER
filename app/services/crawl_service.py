import json
from pathlib import Path
from firecrawl import AsyncFirecrawl
from langchain_community.document_loaders import UnstructuredMarkdownLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_aws import BedrockEmbeddings
from sqlalchemy import text
from app.database import async_session_maker
from app.models import WebsiteDataChunks, WebsiteDataEmbedding, CrawledSource
from app.services.job_store import update_job
from app.settings import Settings

embeddings = BedrockEmbeddings(
    model_id="amazon.titan-embed-text-v2:0",
    region_name="ap-south-1",
    normalize=True,
)

async def source_exists(
        source_url: str
) -> bool:
    async with async_session_maker() as session:
        result = await session.execute(
            text("SELECT id FROM crawedsource WHERE source_url = :url"),
            {"url":source_url},
        )
        return result.fetchone() is not None

async def record_source(
        source_url: str,
        source_type: str,
        chunks_count: int
):
    async with async_session_maker() as session:
        record = CrawledSource(
            source_url=source_url,
            source_type=source_type,
            chunks_count=chunks_count
        )
        session.add(record)
        await session.commit()


async def crawl_website(
        url: str,
        api_key: str,
        limit: int = 10
) -> str:
    crawler = AsyncFirecrawl(api_key=api_key)
    job = await crawler.start_crawl(url, limit=limit)
    status = await crawler.get_crawl_status(job.id)

    markdown_parts = []
    for page in status.data:
        if page.markdown:
            markdown_parts.append(markdown_parts)

    return "\n\n---\n\n".join(markdown_parts)

async def chunk_markdown(
        markdown_content: str,
        source_url: str
):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size = 500,
        chunk_overlap = 100
    )

    docs = splitter.create_documents(
        texts=[markdown_content]
        metadatas=[{"source_url": source_url, "type" : "own_site"}],
    )
    for i, doc in enumerate(docs):
        doc.metadata["chunk_id"] = i
    return docs

async def delete_existing_chunks(
        source_url: str
):
    async with async_session_maker() as session:
        result = await session.execute(
            text("SELECT id FROM websitedatachunks WHERE source_file = :url"),
            {"url": source_url},
        )
        chunk_ids = [row[0] for row in result.fetchall()]
        if chunk_ids:
            await session.execute(
                text("DELETE FROM websitedataembedding WHERE chunk_id = ANY(:ids)"),
                {"ids" : chunk_ids},
            )
            await session.execute(
                text("DELETE FROM websitedatachunks WHERE id = ANY(:ids)"),
                {"ids" : chunk_ids},
            )
        await session.commit()

async def store_chunks_and_embeddings(
        source_url: str,
        chunks
):
    async with async_session_maker() as session:
        for chunk in chunks:
            db_chunk = WebsiteDataChunks(
                source_file=source_url,
                chunk_index=chunk.metadata.get("chunk_id",0),
                content=chunk.page_content,
                metadata_json=json.dumps(chunk.metadata)
            )
            session.add(db_chunk)
            await session.flush()

            embedding_vector = await embeddings.aembed_query(
                chunk,
                page_content
            )

            db_embedding = WebsiteDataEmbedding(
                chunk_id=db_chunk.id,
                embedding=embedding_vector,
                model_id="amazon.titan-embed-text-v2:0"
            )
            session.add(db_embedding)
        await session.commit()
        return len(chunks)

async def process_crawl_job(
        job_id: str,
        url: str,
        limit: int
):
    try:
        exists = await source_exists(url)
        if exists:
            update_job(
                job_id,
                status = "already_exists",
                chunk_created = 0
            )
            return

        markdown = await crawl_website(url, Settings.firecrawl_api, limit)
        chunks = await chunk_markdown(markdown, url)
        await delete_existing_chunks(url)
        count = await store_chunks_and_embeddings(url, chunks)
        await record_source(url, "website", count)
        update_job(
            job_id,
            status = "completed",
            chunks_created=count
        )
    except Exception as e:
        update_job(job_id, status="failed")
import json
from pathlib import Path
from firecrawl import AsyncFirecrawl
from langchain_community.document_loaders import UnstructuredMarkdownLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy import text
from app.database import async_session_maker
from app.models import WebsiteDataChunks, WebsiteDataEmbedding
from app.services.job_store import update_job
from app.settings import Settings


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
    
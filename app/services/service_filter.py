from langchain_aws import BedrockEmbeddings
from sqlmodel import select

from app.database import async_session_maker
from app.models import WebsiteDataChunks, WebsiteDataEmbedding

embeddings = BedrockEmbeddings(
    model_id="amazon.titan-embed-text-v2:0",
    region_name="ap-south-1",
    normalize=True,
)

SERVICES_QUERY = "services offered pricing packages activities entertainment for park tickets"


async def get_service_chunks(limit: int = 15, owners: list[str] | None = None) -> list[dict]:
    query_vector = await embeddings.aembed_query(SERVICES_QUERY)
    dist_col = WebsiteDataEmbedding.embedding.l2_distance(query_vector).label("dist")
    async with async_session_maker() as session:
        stmt = (
            select(
                WebsiteDataChunks.content,
                WebsiteDataChunks.source_file,
                WebsiteDataChunks.owner,
                dist_col,
            )
            .join(
                WebsiteDataEmbedding,
                WebsiteDataEmbedding.chunk_id == WebsiteDataChunks.id,
            )
            .order_by(dist_col)
            .limit(limit)
        )
        if owners:
            stmt = stmt.where(WebsiteDataChunks.owner.in_(owners))
        rows = (await session.execute(stmt)).all()
        return [
            {"content": row[0], "source": row[1], "owner": row[2], "dist": row[3]} for row in rows
        ]

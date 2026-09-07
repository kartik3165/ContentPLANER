from sqlalchemy import text
from langchain_aws import BedrockEmbeddings
from app.database import async_session_maker

embeddings = BedrockEmbeddings(
    model_id="amazon.titan-embed-text-v2:0",
    region_name="ap-south-1",
    normalize=True
)

SERVICES_QUERY = "services offered pricing packanges activities entertainments for park tickets"

async def get_service_chunks(
        limit: int = 15,
        owners: list[str] | None = None
) -> list[dict]:
    query = await embeddings.aembed_query(SERVICES_QUERY)
    if owners:
        owner_filter = "AND c.owner = ANY(:owners)"
    async with async_session_maker() as s:
        res = await s.execute(text(f"""
            SELECT c.content, c.source_file, c.owner,
                e.embedding <=> :qv AS dist
            FROM websitedatachunks c
            JOIN websitedataembedding e ON c.id = e.chunk_id
            WHERE 1=1 {owner_filter}
            ORDER BY e.embedding <=> :qv LIMIT :k
        """), {"qv": str(query), "k": limit, "owners": owners or []})

    return [{"content": row[0], "source": row[1], "owner": row[2], "dist": row[3]} for row in res.fetchall()]
from sqlmodel import Field, SQLModel, Relationship
from datetime import datetime
from pgvector.sqlalchemy import Vector
from enum import Enum

class PostOwnerType(str, Enum):
    OWN = "own",
    COMPETITION = "competition"

class InstagramPost(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    PostOwnerType: PostOwnerType = Field(default=PostOwnerType.OWN) # type: ignore
    postType: str
    caption: str
    hashtags: str
    postUrl: str 
    commentsCount: int
    likesCount: int
    videoViewCount: int
    displayUrl: str
    altText: int 
    childPosts: str

class WebsiteDataChunks(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    source_file: str
    chunk_index: int
    content: str
    metadata_json: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    embeddings: list["WebsiteDataEmbedding"] = Relationship(back_populates="chunk")

class WebsiteDataEmbedding(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    chunk_id: int = Field(foreign_key="WebsiteDataChunks.id")
    embedding: list[float] = Field(sa_type=Vector(1024))
    model_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    chunk: WebsiteDataChunks = Relationship(back_populates="embeddings")

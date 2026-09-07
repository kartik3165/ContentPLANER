from sqlmodel import Field, SQLModel, Relationship
from datetime import datetime, date
from pgvector.sqlalchemy import Vector
from enum import Enum

class PostOwnerType(str, Enum):
    OWN = "own",
    COMPETITION = "competition"

class InstagramPost(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    PostOwnerType: PostOwnerType = Field(default=PostOwnerType.OWN) # type: ignore
    owner_username:str = Field(default="", index=True)
    postType: str = Field(default="")
    caption: str = Field(default="")
    hashtags: str = Field(default="")
    postUrl: str = Field(default="")
    commentsCount: int = Field(default=0)
    likesCount: int = Field(default=0)
    videoViewCount: int = Field(default=0)
    displayUrl: str = Field(default="")
    altText: str =  Field(default="")
    childPosts: str = Field(default="")
    engagement_score: float = Field(default=0.0, index=True)

class WebsiteDataChunks(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    source_file: str
    owner: str = Field(default="own", index=True)
    chunk_index: int
    content: str
    metadata_json: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    embeddings: list["WebsiteDataEmbedding"] = Relationship(back_populates="chunk")

class WebsiteDataEmbedding(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    chunk_id: int = Field(foreign_key="WebsiteDataChunks.id")
    embedding: list[float] = Field(sa_type=Vector(1024)) # type: ignore
    model_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    chunk: WebsiteDataChunks = Relationship(back_populates="embeddings")

class CrawledSource(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    source_url: str = Field(unique=True, index=True)
    source_type: str
    chunks_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Competitor(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    instagram_handle: str | None = Field(default=None, index=True)
    website_url: str | None = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ContentPlan(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    start_date: date
    num_days: int
    plan_json: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


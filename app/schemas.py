from datetime import date

from pydantic import BaseModel, HttpUrl


class CrawlRequest(BaseModel):
    owner: str = "own"
    url: HttpUrl
    limit: int = 10
    refresh: bool = False


class CrawlResponse(BaseModel):
    job_id: str
    source_url: str
    status: str
    chunks_created: int


class JobStatusResponse(BaseModel):
    job_id: str
    source_url: str
    status: str
    chunks_created: int


class InstagramRequest(BaseModel):
    username: str
    owner_type: str = "own"
    refresh: bool = False


class CompetitorCreate(BaseModel):
    instagram_handle: str | None = None
    website_url: str | None = None


class PlanRequest(BaseModel):
    num_days: int = 7
    start_date: date

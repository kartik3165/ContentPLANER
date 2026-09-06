from pydantic import BaseModel, HttpUrl

class CrawlRequest(BaseModel):
    url: HttpUrl
    limit: int = 10

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
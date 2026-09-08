import uuid

from fastapi import APIRouter, BackgroundTasks
from sqlmodel import select

from app.database import async_session_maker
from app.models import Competitor, PostOwnerType
from app.schemas import (
    CompetitorCreate,
    CrawlRequest,
    CrawlResponse,
    InstagramRequest,
    JobStatusResponse,
    PlanRequest,
)
from app.services.crawl_instagram import process_instagram_job
from app.services.crawl_service import process_crawl_job
from app.services.job_store import create_job, get_job
from app.services.plan_service import generate_plan

router = APIRouter()


@router.post("/crawl", response_model=CrawlResponse)
async def crawl_endpoint(req: CrawlRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    create_job(job_id, str(req.url))
    background_tasks.add_task(process_crawl_job, job_id, str(req.url), req.limit, req.owner)
    return CrawlResponse(
        job_id=job_id, source_url=str(req.url), status="processing", chunks_created=0
    )


@router.post("/instagram", response_model=CrawlResponse)
async def instagram_endpoint(req: InstagramRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    create_job(job_id, req.username)
    owner_type = PostOwnerType.COMPETITION if req.owner_type == "competition" else PostOwnerType.OWN
    background_tasks.add_task(process_instagram_job, job_id, req.username, owner_type)
    return CrawlResponse(
        job_id=job_id, source_url=req.username, status="processing", chunks_created=0
    )


@router.post("/competitors")
async def add_competitor(req: CompetitorCreate):
    async with async_session_maker() as session:
        session.add(Competitor(instagram_handle=req.instagram_handle, website_url=req.website_url))
        await session.commit()
    return {"status": "added"}


@router.get("/competitors")
async def list_competitors():
    async with async_session_maker() as session:
        result = await session.execute(select(Competitor))
        return list(result.scalars().all())


@router.post("/plan")
async def create_plan(req: PlanRequest):
    return await generate_plan(req.num_days, req.start_date)


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    job = get_job(job_id)
    if not job:
        return JobStatusResponse(job_id=job_id, source_url="", status="not_found", chunks_created=0)
    return job

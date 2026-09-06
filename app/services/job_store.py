from app.schemas import JobStatusResponse

jobs: dict[str, JobStatusResponse] = {}

def create_job(job_id: str, source_url: str) -> JobStatusResponse:

    job = JobStatusResponse(
        job_id=job_id,
        source_url=source_url,
        status="processing",
        chunks_created=0
    )
    jobs[job_id] = job
    return job

def update_job(job_id: str, **kwargs):
    if job_id in  jobs:
        for k, v in kwargs.items():
            setattr(jobs[job_id], k, v)

def get_job(job_id: str) -> JobStatusResponse | None:
    return jobs.get(job_id)
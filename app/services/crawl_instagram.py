import json 
import os
from apify_client import ApifyClientAsync
from sqlalchemy import text
from app.database import async_session_maker
from app.models import InstagramPost, CrawledSource
from app.services.crawl_service import source_exists, record_source
from app.services.job_store import update_job
from app.settings import Settings

async def get_insta_account_info(
        user_name: str,
        api_key: str
):
    client = ApifyClientAsync(api_key)
    run = await client.actor("dSCLg0C3YEZ83HzYX").call(
        run_input={
            "username" : [user_name],
            "includeAboutSection" : False
        }
    )
    dataset = client.dataset(run.default_dataset_id)
    async for item in dataset.iterate_items():
        return item
    return None

async def store_instagram_data(
        username: str, 
        data: dict
) -> int:
    async with async_session_maker() as session:
        posts = data.get("latestPosts", [])

        for p in posts:
            session.add(InstagramPost(
                PostOwnerType="own",
                postType=p.get("type", ""),
                caption=p.get("caption", "") or "",
                hashtags=json.dumps(p.get("hashtags", [])),
                postUrl=p.get("url", ""),
                commentsCount=p.get("commentsCount", 0),
                likesCount=p.get("likesCount", 0),
                videoViewCount=p.get("videoViewCount", 0),
                displayUrl=p.get("displayUrl", "") or "",
                altText=0,
                childPosts=json.dumps(p.get("childPosts", [])),
            ))

        await session.commit()

        return len(posts)

async def process_instagram_job(
        job_id: str,
        username: str,
    ):
    try:
        if await source_exists(username, "instagram"):
            update_job(
                job_id, 
                status="already_exists",
                chunks_created=0
            )
            return 
        data = await get_insta_account_info(username, Settings.apify_api)
        if not data:
            update_job(job_id, status="failed")
            return
        count = await store_instagram_data(username, data)
        await record_source(username, "instagram", count)
        update_job(
            job_id,
            status="completed",
            chunks_created=count
        )
    except Exception:
        update_job(job_id, status="failed")
        raise
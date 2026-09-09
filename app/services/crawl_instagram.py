import json

from apify_client import ApifyClientAsync
from sqlmodel import select

from app.database import async_session_maker
from app.models import InstagramPost, PostOwnerType
from app.services.crawl_service import delete_source_record, record_source, source_exists
from app.services.job_store import update_job


def calc_score(likes: int, comments: int, views: int) -> float:
    return likes * 1.0 + comments * 3.0 + views * 0.1


async def get_insta_account_info(user_name: str, api_key: str):
    client = ApifyClientAsync(api_key)
    run = await client.actor("dSCLg0C3YEZ83HzYX").call(
        run_input={
            "usernames": [user_name],
            "includeAboutSection": False,
        }
    )
    dataset = client.dataset(run.default_dataset_id)
    async for item in dataset.iterate_items():
        return item
    return None


async def store_instagram_data(
    username: str, data: dict, owner_type: PostOwnerType = PostOwnerType.OWN
) -> int:
    async with async_session_maker() as session:
        posts = data.get("latestPosts", [])
        for p in posts:
            likes = p.get("likesCount", 0) or 0
            comments = p.get("commentsCount", 0) or 0
            views = p.get("videoViewCount", 0) or 0
            session.add(
                InstagramPost(
                    post_owner_type=owner_type,
                    owner_username=username,
                    postType=p.get("type", "") or "",
                    caption=p.get("caption", "") or "",
                    hashtags=json.dumps(p.get("hashtags", [])),
                    postUrl=p.get("url", "") or "",
                    commentsCount=comments,
                    likesCount=likes,
                    videoViewCount=views,
                    displayUrl=p.get("displayUrl", "") or "",
                    altText="",
                    childPosts=json.dumps(p.get("childPosts", [])),
                    engagement_score=calc_score(likes, comments, views),
                )
            )
        await session.commit()
        return len(posts)


async def delete_existing_instagram_posts(username: str):
    async with async_session_maker() as session:
        result = await session.execute(
            select(InstagramPost).where(InstagramPost.owner_username == username)
        )
        for post in result.scalars().all():
            await session.delete(post)
        await session.commit()


async def process_instagram_job(
    job_id: str,
    username: str,
    owner_type: PostOwnerType = PostOwnerType.OWN,
    refresh: bool = False,
):
    from app.settings import get_settings

    settings = get_settings()
    try:
        if await source_exists(username, "instagram") and not refresh:
            update_job(job_id, status="already_exists", chunks_created=0)
            return
        data = await get_insta_account_info(username, settings.apify_api)
        if not data:
            update_job(job_id, status="failed")
            return
        await delete_existing_instagram_posts(username)
        await delete_source_record(username, "instagram")
        count = await store_instagram_data(username, data, owner_type)
        await record_source(username, "instagram", count)
        update_job(job_id, status="completed", chunks_created=count)
    except Exception:
        update_job(job_id, status="failed")
        raise

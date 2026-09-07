from sqlmodel import select
from app.database import async_session_maker
from app.models import InstagramPost, PostOwnerType

def cal_score(
        likes: int,
        comments: int,
        views: int,
) -> float:
    return likes * 1.0 + comments * 3.0 + views * 0.1

async def get_top_competitor_posts(
        limit: int = 10
) -> list[InstagramPost]:
    async with async_session_maker() as session:
        res = await session.execute(
            select(InstagramPost)
            .where(InstagramPost.PostOwnerType == PostOwnerType.COMPETITION)
            .order_by(InstagramPost.engagement_score.desc())
            .limit(limit)
        )
        return list(res.scalars().all())

async def update_engagement_scores():
    async with async_session_maker() as session:
        res = await session.execute(select(InstagramPost))
        for post in res.scalars().all():
            post.engagement_score = cal_score(
                post.likesCount,
                post.commentsCount,
                post.videoViewCount
            )
            session.add(post)
        await session.commit()
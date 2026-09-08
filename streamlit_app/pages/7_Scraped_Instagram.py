import asyncio
import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlmodel import select  # noqa: E402, I001

from app.database import async_session_maker  # noqa: E402
from app.models import InstagramPost, PostOwnerType  # noqa: E402


st.set_page_config(page_title="Scraped Instagram Data", layout="wide")
st.title(":material/photo_library: Scraped Instagram Data")
st.caption("Review saved posts, owners, captions, and engagement metrics.")


async def load_posts(
    owner_type: PostOwnerType | None = None,
    username: str | None = None,
) -> list[InstagramPost]:
    async with async_session_maker() as session:
        statement = select(InstagramPost).order_by(InstagramPost.engagement_score.desc())
        if owner_type:
            statement = statement.where(InstagramPost.post_owner_type == owner_type)
        if username:
            statement = statement.where(InstagramPost.owner_username == username)
        result = await session.execute(statement)
        return list(result.scalars().all())


all_posts = asyncio.run(load_posts())
if not all_posts:
    st.info("No Instagram data has been scraped yet.")
    st.stop()

accounts = sorted({post.owner_username for post in all_posts})
owner_filter = st.selectbox("Owner type", ["All", "Own", "Competition"])
account_filter = st.selectbox("Account", ["All accounts", *accounts])

owner_type = {
    "Own": PostOwnerType.OWN,
    "Competition": PostOwnerType.COMPETITION,
}.get(owner_filter)
username = None if account_filter == "All accounts" else account_filter
posts = asyncio.run(load_posts(owner_type, username))

metric_1, metric_2, metric_3 = st.columns(3)
metric_1.metric("Posts", len(posts))
metric_2.metric("Likes", f"{sum(post.likesCount for post in posts):,}")
metric_3.metric("Comments", f"{sum(post.commentsCount for post in posts):,}")

st.dataframe(
    [
        {
            "Account": post.owner_username,
            "Owner": post.post_owner_type.value,
            "Type": post.postType,
            "Likes": post.likesCount,
            "Comments": post.commentsCount,
            "Views": post.videoViewCount,
            "Score": round(post.engagement_score, 1),
            "Post URL": post.postUrl,
        }
        for post in posts
    ],
    use_container_width=True,
    hide_index=True,
    column_config={"Post URL": st.column_config.LinkColumn("Post URL")},
)

st.subheader("Post details")
for _index, post in enumerate(posts):
    label = f"{post.owner_username} · {post.postType or 'post'} · score {post.engagement_score:.1f}"
    with st.expander(label):
        if post.displayUrl:
            st.image(post.displayUrl, width=320)
        st.markdown(post.caption or "No caption saved.")
        st.write(
            {
                "hashtags": post.hashtags,
                "likes": post.likesCount,
                "comments": post.commentsCount,
                "views": post.videoViewCount,
                "post_url": post.postUrl,
            }
        )

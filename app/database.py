import os
from collections.abc import AsyncGenerator

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    engine = create_async_engine(DATABASE_URL, echo=True)

    async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def get_session() -> AsyncGenerator[AsyncSession]:
        async with async_session_maker() as session:
            yield session

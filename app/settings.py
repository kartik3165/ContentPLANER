import os
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    calendar_api: str = os.getenv("CALENDARIFIC_API_KEY")  # type: ignore
    firecrawl_api: str = os.getenv("FIRECRAWL_API_KEY")  # type: ignore
    apify_api: str = os.getenv("APIFY_API_KEY")  # type: ignore


@lru_cache
def get_settings() -> Settings:
    return Settings()

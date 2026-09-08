from datetime import date, timedelta

import httpx


async def get_festivals(start: date, days: int) -> list[dict]:
    from app.settings import get_settings

    settings = get_settings()
    end = start + timedelta(days=days)
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://calendarific.com/api/v2/holidays",
            params={
                "api_key": settings.calendar_api,
                "country": "IN",
                "year": start.year,
            },
        )
        response.raise_for_status()
    out = []
    for h in response.json()["response"]["holidays"]:
        d = date.fromisoformat(h["date"]["iso"])
        if start <= d <= end:
            out.append(
                {
                    "name": h["name"],
                    "date": h["date"]["iso"],
                    "description": h["description"],
                }
            )
    return out

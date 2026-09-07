import httpx, os
from datetime import date, timedelta
from app.settings import Settings

async def get_festivals(start: date, days: int) -> list[dict]:
    end = start + timedelta(days=days)

    async with httpx.AsyncClient() as c:
        r = await c.get(
            "https://calendarific.com/api/v2/holidays",
            params={
                "api_key": Settings.calendar_api,
                "country": "IN",
                "year": start.year,
            },
        )
        r.raise_for_status()

        out = []

        for h in r.json()["response"]["holidays"]:
            d = date.fromisoformat(h["date"]["iso"])

            if start <= d <= end:
                out.append({
                    "name": h["name"],
                    "date": h["date"]["iso"],
                    "description": h["description"],
                })

        return out
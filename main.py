from datetime import date, timedelta
import httpx
import asyncio
from dotenv import load_dotenv
import os

load_dotenv()

cal_api = os.getenv("CALENDARIFIC_API_KEY")

async def get_festival(api_key: str, start_date: date = date.today(), end_date_days :int = 6) -> list:
    country = "IN"
    year = start_date.year
    end_date = start_date + timedelta(days=end_date_days)

    festival_dates = []

    async with httpx.AsyncClient() as client:
        all_holidays = await client.get(
            "https://calendarific.com/api/v2/holidays",
            params={
                "api_key": api_key,
                "country": country,
                "year": year,
            }
        )

        all_holidays.raise_for_status()

    holidays = all_holidays.json()["response"]["holidays"]

    for week_holidays in holidays:
        holiday_date = date.fromisoformat(
            week_holidays["date"]["iso"]
        )

        if start_date <= holiday_date <= end_date:
            festival_dates.append({
                "name": week_holidays["name"],
                "date": week_holidays["date"]["iso"],
                "description": week_holidays["description"]
            })

    return festival_dates


async def main():
    print(await get_festival(
        api_key=cal_api,
        end_date_days=25
    ))

asyncio.run(main())
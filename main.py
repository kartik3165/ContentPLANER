import requests
from dotenv import load_dotenv
import os

load_dotenv()

cal_api = os.getenv("CALENDARIFIC_API_KEY")
print(cal_api) 
def get_cal():
    try:
        data = requests.get(
            "https://calendarific.com/api/v2/holidays",
            params={
                "api_key": cal_api, 
                "country": "US", 
                "year": 2026
            },
        )
        # print(r.json()["response"]["holidays"])
    except Exception as e:
        print(f"Error {e}")
    return data.json()

print(get_cal())
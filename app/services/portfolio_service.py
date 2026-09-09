import json
import re

from langchain_aws import ChatBedrock
from sqlmodel import select

from app.database import async_session_maker
from app.models import WebsiteDataChunks

_llm = ChatBedrock(
    model="apac.amazon.nova-lite-v1:0",
    region_name="ap-south-1",
    beta_use_converse_api=True,
    max_tokens=2048,
    temperature=0.1,
)

_SYSTEM_PROMPT = """You are a portfolio intelligence analyst.

Compare OWN WEBSITE CONTENT with COMPETITOR WEBSITE CONTENT.

Rules:
- HAVE IN PORTFOLIO may contain only services, activities, packages, or offers
  explicitly supported by OWN WEBSITE CONTENT.
- NOT IN OUR PORTFOLIO may contain only competitor offerings that are not
  supported by OWN WEBSITE CONTENT.
- Never infer that the OWN brand provides a competitor-only offering.
- Merge duplicate services and keep names concise.
- Include short evidence from the provided text, not invented facts.
- If the data does not support a conclusion, leave that item out.

Return strict JSON only:
{
  "have_in_portfolio": [
    {"service_name": "...", "evidence": "...", "source": "..."}
  ],
  "not_in_portfolio": [
    {"service_name": "...", "competitor": "...", "evidence": "...", "opportunity": "..."}
  ]
}
"""


async def _load_content(owner: str) -> list[WebsiteDataChunks]:
    async with async_session_maker() as session:
        result = await session.execute(
            select(WebsiteDataChunks)
            .where(WebsiteDataChunks.owner == owner)
            .order_by(WebsiteDataChunks.source_file, WebsiteDataChunks.chunk_index)
        )
        return list(result.scalars().all())


def _repair_json(raw: str) -> str:
    text = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    return match.group(0) if match else text


async def analyze_portfolio() -> dict:
    own = await _load_content("own")
    competitors = await _load_content("competition")
    if not own and not competitors:
        return {"have_in_portfolio": [], "not_in_portfolio": []}

    def format_content(items: list[WebsiteDataChunks], max_chars: int = 5000) -> str:
        parts: list[str] = []
        used = 0
        for item in items:
            part = f"SOURCE: {item.source_file}\nCONTENT: {item.content[:700]}"
            if used + len(part) > max_chars:
                break
            parts.append(part)
            used += len(part)
        return "\n".join(parts)

    own_text = format_content(own)
    competitor_text = format_content(competitors)
    prompt = (
        "OWN WEBSITE CONTENT:\n"
        f"{own_text or '[No own website content scraped]'}\n\n"
        "COMPETITOR WEBSITE CONTENT:\n"
        f"{competitor_text or '[No competitor website content scraped]'}\n\n"
        "Analyze the portfolio now."
    )
    raw = str((await _llm.ainvoke([("system", _SYSTEM_PROMPT), ("human", prompt)])).content)
    try:
        result = json.loads(_repair_json(raw))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Portfolio analysis returned invalid JSON: {exc}") from exc
    return {
        "have_in_portfolio": result.get("have_in_portfolio", [])
        if isinstance(result.get("have_in_portfolio", []), list)
        else [],
        "not_in_portfolio": result.get("not_in_portfolio", [])
        if isinstance(result.get("not_in_portfolio", []), list)
        else [],
    }

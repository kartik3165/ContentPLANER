import json
from datetime import date

from langchain_aws import ChatBedrock

from app.database import async_session_maker
from app.models import ContentPlan
from app.services.engagement import get_own_posts, get_top_competitor_posts
from app.services.festival import get_festivals
from app.services.prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from app.services.service_filter import get_service_chunks

_llm = ChatBedrock(
    model_id="meta.llama3-8b-instruct-v1:0",
    region_name="ap-south-1",
    max_tokens=4096,
    temperature=0.2,
)


async def build_context(top_k: int = 10, chunk_k: int = 15) -> str:
    comp_posts = await get_top_competitor_posts(top_k)
    own_posts = await get_own_posts(5)
    chunks = await get_service_chunks(chunk_k)
    lines = ["== TOP COMPETITOR POSTS (by engagement_score) =="]
    for p in comp_posts:
        lines.append(
            f"- @{p.owner_username} score={p.engagement_score:.1f} "
            f"likes={p.likesCount} comments={p.commentsCount} "
            f"views={p.videoViewCount}\n"
            f"  caption: {p.caption[:500]}\n  hashtags: {p.hashtags}\n  url: {p.postUrl}"
        )
    lines.append("\n== OWN POSTS ==")
    for p in own_posts:
        lines.append(f"- caption: {p.caption[:300]} | likes={p.likesCount}")
    lines.append("\n== SERVICE CHUNKS (own + competitor sites) ==")
    for c in chunks:
        lines.append(f"- [{c['owner']}] {c['source']}: {c['content'][:800]}")
    return "\n".join(lines)


async def generate_plan(num_days: int, start: date) -> dict:
    festivals = await get_festivals(start, num_days)
    context = await build_context()
    fest_txt = (
        "\n".join(f"- {f['date']}: {f['name']} — {f['description']}" for f in festivals)
        or "No major festivals."
    )
    user_prompt = USER_PROMPT_TEMPLATE.format(
        num_days=num_days,
        start_date=start.isoformat(),
        festivals=fest_txt,
        context=context,
    )
    messages = [("system", SYSTEM_PROMPT), ("human", user_prompt)]
    raw = str((await _llm.ainvoke(messages)).content).strip()

    def _repair_json(s: str) -> str:
        import re

        # strip code fences
        t = s.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        # extract outermost JSON object
        m = re.search(r"\{.*\}", t, re.DOTALL)
        if m:
            t = m.group(0)
        # remove trailing commas before } or ]
        t = re.sub(r",\s*}", "}", t)
        t = re.sub(r",\s*]", "]", t)
        # fix unescaped newlines inside strings is hard — rely on LLM fix; fallback to repair
        return t

    txt = _repair_json(raw)
    try:
        plan = json.loads(txt)
    except json.JSONDecodeError as e:
        # last resort: log raw and raise with context

        raise ValueError(f"Failed to parse LLM JSON: {e}\nRaw snippet:\n{txt[:2000]}") from e
    # ensure correct shape
    if "days" not in plan:
        plan = {"days": plan if isinstance(plan, list) else []}
    if not isinstance(plan["days"], list):
        raise ValueError("LLM response must contain a JSON array named 'days'.")
    if len(plan["days"]) != num_days:
        raise ValueError(
            f"LLM returned {len(plan['days'])} days, but {num_days} were requested. "
            "Try again or request fewer days."
        )
    async with async_session_maker() as session:
        session.add(ContentPlan(start_date=start, num_days=num_days, plan_json=json.dumps(plan)))
        await session.commit()
    return plan

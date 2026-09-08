import asyncio

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from sqlmodel import select

from app.database import async_session_maker
from app.models import Competitor

st.set_page_config(page_title="Competitors", layout="wide")
st.title(":material/group: Competitors")

with st.form("add"):
    ig = st.text_input("Competitor IG handle (without @)")
    web = st.text_input("Competitor website URL")
    ok = st.form_submit_button("Add", type="primary")

if ok and (ig or web):

    async def add():
        async with async_session_maker() as session:
            session.add(Competitor(instagram_handle=ig or None, website_url=web or None))
            await session.commit()

    asyncio.run(add())
    st.success("Added!")
    st.rerun()


async def load():
    async with async_session_maker() as session:
        result = await session.execute(select(Competitor))
        return list(result.scalars().all())


for c in asyncio.run(load()):
    st.markdown(
        f"- IG: `{c.instagram_handle or '-'}` | Web: `{c.website_url or '-'}` | {c.created_at}"
    )

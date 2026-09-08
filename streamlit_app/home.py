import streamlit as st

st.set_page_config(page_title="ContentPlan", page_icon=":material/edit_note:", layout="wide")
st.title("ContentPlan")
st.markdown("Use the sidebar pages to Crawl Site, Scrape Instagram, or Search.")

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown("### :material/language: Crawl Site")
    st.page_link("pages/1_Crawl_Site.py", label="Go to Crawl Site")
with c2:
    st.markdown("### :material/photo_camera: Instagram")
    st.page_link("pages/2_Instagram.py", label="Go to Instagram")
with c3:
    st.markdown("### :material/search: Search")
    st.page_link("pages/3_Search.py", label="Go to Search")

c4, c5 = st.columns(2)
with c4:
    st.markdown("### :material/group: Competitors")
    st.page_link("pages/4_Competitors.py", label="Manage Competitors")
with c5:
    st.markdown("### :material/calendar_month: Content Plan")
    st.page_link("pages/5_Content_Plan.py", label="Generate Plan")

c6, c7 = st.columns(2)
with c6:
    st.markdown("### :material/description: Scraped Website Data")
    st.page_link("pages/6_Scraped_Website.py", label="View Website Data")
with c7:
    st.markdown("### :material/photo_library: Scraped Instagram Data")
    st.page_link("pages/7_Scraped_Instagram.py", label="View Instagram Data")

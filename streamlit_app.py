import streamlit as st

pages = [
    st.Page(
        "01_registration_crf.py",
        title="登録判定・中央登録",
        default=True,
    ),
    st.Page(
        "02_perioperative_30d_crf.py",
        title="周術期・術後30日",
    ),
    st.Page(
        "03_day90_crf.py",
        title="術後90日",
    ),
    st.Page(
        "04_followup_crf.py",
        title="定期経過（6〜24か月）",
    ),
]

page = st.navigation(pages, position="sidebar")
page.run()

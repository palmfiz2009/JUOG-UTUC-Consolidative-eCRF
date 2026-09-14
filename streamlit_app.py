import streamlit as st

st.set_page_config(page_title="JUOG UTUC_Consolidative eCRF", layout="wide")

pages = [
    st.Page("01_registration_crf.py", title="中央MDT審査申請", default=True),
    st.Page("02_perioperative_30d_crf.py", title="周術期・術後30日"),
    st.Page("03_day90_crf.py", title="術後90日"),
    st.Page("04_followup_crf.py", title="定期経過（6〜24か月）"),
    st.Page("06_mdt_reviewer.py", title="中央MDT判定者専用"),
    st.Page("05_admin_mdt_registration.py", title="事務局専用：中央MDT集約・正式登録"),
]

page = st.navigation(pages, position="sidebar")
page.run()

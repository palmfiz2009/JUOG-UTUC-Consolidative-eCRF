from urllib.parse import urlencode

import streamlit as st

st.set_page_config(page_title="JUOG UTUC_Consolidative eCRF", layout="wide")

pages = {
    "症例入力": [
        st.Page("01_registration_crf.py", title="中央MDT審査申請", default=True),
        st.Page("02_perioperative_30d_crf.py", title="周術期・術後30日"),
        st.Page("03_day90_crf.py", title="術後90日"),
        st.Page("04_followup_crf.py", title="定期経過（6〜24か月）"),
    ],
    "関係者専用": [
        st.Page("06_mdt_reviewer.py", title="中央MDT判定者専用"),
        st.Page("05_admin_mdt_registration.py", title="事務局専用：中央MDT集約・正式登録"),
    ],
}

page = st.navigation(pages, position="sidebar")

# ---------------- sidebar support ----------------
support_query = urlencode({
    "view": "cm",
    "fs": "1",
    "to": "yoshida.tks@kmu.ac.jp",
    "su": "JUOG UTUC eCRF 不具合報告",
    "body": (
        "画面名：\n"
        "受付番号／JUOG登録番号：\n"
        "発生日時：\n"
        "エラー内容：\n\n"
        "※患者氏名、カルテ番号、生年月日などの個人情報は記載しないでください。"
    ),
})
support_url = f"https://mail.google.com/mail/?{support_query}"

st.sidebar.divider()
st.sidebar.link_button("✉ 不具合を連絡", support_url, use_container_width=True)
st.sidebar.caption("※個人情報はメールに記載しないでください。")

page.run()

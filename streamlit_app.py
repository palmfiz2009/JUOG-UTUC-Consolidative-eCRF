from urllib.parse import quote

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
support_subject = quote("JUOG UTUC eCRF 不具合報告")
support_body = quote(
    "画面名：\n"
    "JUOG登録番号：\n"
    "発生日時：\n"
    "エラー内容：\n\n"
    "※患者氏名、カルテ番号、生年月日などの個人情報は記載しないでください。"
)
support_mailto = (
    "mailto:yoshida.tks@kmu.ac.jp"
    f"?subject={support_subject}&body={support_body}"
)

st.sidebar.divider()
st.sidebar.markdown("### サポート")
st.sidebar.caption("eCRF操作中の不具合・エラー")
st.sidebar.markdown(f"[📩 サポートに連絡]({support_mailto})")
st.sidebar.caption("患者氏名・カルテ番号等の個人情報はメールに記載しないでください。")

page.run()

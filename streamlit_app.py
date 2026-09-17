import re
from datetime import datetime

import streamlit as st

from juog_common import FACILITY_NAMES, TZ, send_support_email, valid_email, valid_registration_id

st.set_page_config(page_title="JUOG UTUC_Consolidative eCRF", layout="wide")

# Make vertical scrollbars easier to grab without changing page content.
st.markdown(
    """
    <style>
    html { scrollbar-width: auto; }
    ::-webkit-scrollbar { width: 14px; height: 14px; }
    ::-webkit-scrollbar-thumb {
        background: #94A3B8;
        border-radius: 999px;
        border: 3px solid transparent;
        background-clip: content-box;
        min-height: 44px;
    }
    ::-webkit-scrollbar-track { background: transparent; }
    </style>
    """,
    unsafe_allow_html=True,
)

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

# ---------------- compact sidebar support ----------------
st.sidebar.divider()
with st.sidebar.popover("✉ 不具合を連絡", use_container_width=True):
    st.caption("eCRFの不具合・エラーを研究事務局へ送信します。")

    with st.form("juog_support_form", clear_on_submit=False):
        id_kind = st.selectbox(
            "症例識別*",
            ["JUOG登録番号", "MDT受付番号", "未発番"],
            key="support_id_kind",
        )

        case_id = ""
        facility_name = ""
        if id_kind == "JUOG登録番号":
            case_id = st.text_input("JUOG登録番号*", placeholder="JUOG-001", key="support_juog_id").strip().upper()
        elif id_kind == "MDT受付番号":
            case_id = st.text_input("MDT受付番号*", placeholder="JUOG-SCR-001", key="support_scr_id").strip().upper()
        else:
            facility_name = st.selectbox(
                "施設名*",
                ["選択してください"] + FACILITY_NAMES,
                key="support_facility",
            )

        screen_name = st.selectbox(
            "発生画面*",
            [
                "中央MDT審査申請",
                "周術期・術後30日",
                "術後90日",
                "定期経過（6〜24か月）",
                "中央MDT判定者専用",
                "事務局専用：中央MDT集約・正式登録",
                "その他",
            ],
            key="support_screen",
        )
        reply_email = st.text_input("返信先メールアドレス*", key="support_reply_email").strip()
        details = st.text_area("不具合・エラー内容*", height=110, key="support_details").strip()
        st.caption("患者氏名・カルテ番号・生年月日等の個人情報は入力しないでください。")

        submitted = st.form_submit_button("送信", use_container_width=True)

    if submitted:
        errors = []
        if id_kind == "JUOG登録番号" and not valid_registration_id(case_id):
            errors.append("JUOG登録番号を正しい形式（例：JUOG-001）で入力してください。")
        elif id_kind == "MDT受付番号" and not re.fullmatch(r"JUOG-SCR-\d{3,4}", case_id):
            errors.append("MDT受付番号を正しい形式（例：JUOG-SCR-001）で入力してください。")
        elif id_kind == "未発番" and facility_name == "選択してください":
            errors.append("施設名を選択してください。")

        if not valid_email(reply_email):
            errors.append("返信先メールアドレスを正しく入力してください。")
        if not details:
            errors.append("不具合・エラー内容を入力してください。")

        if errors:
            for message in errors:
                st.error(message)
        else:
            identifier = case_id if id_kind != "未発番" else f"未発番 / {facility_name}"
            occurred_at = datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S %Z")
            subject = f"JUOG UTUC eCRF 不具合報告 [{identifier}]"
            content = (
                "JUOG UTUC_Consolidative eCRF サポート依頼\n\n"
                f"症例識別：{identifier}\n"
                f"発生画面：{screen_name}\n"
                f"送信日時：{occurred_at}\n"
                f"返信先メールアドレス：{reply_email}\n\n"
                "不具合・エラー内容：\n"
                f"{details}\n\n"
                "※患者氏名、カルテ番号、生年月日等の個人情報は入力しない運用です。"
            )
            ok, _err = send_support_email(subject, content)
            if ok:
                st.success("研究事務局へ送信しました。")
            else:
                st.error("送信できませんでした。時間をおいて再度お試しいただくか、yoshida.tks@kmu.ac.jp へご連絡ください。")

page.run()

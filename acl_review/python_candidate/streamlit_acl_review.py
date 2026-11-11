"""Review-only OIDC -> signed server ACL context check. No business pages."""
import streamlit as st
from streamlit_unified_client import _post

def run():
    st.set_page_config(page_title="JUOG isolated ACL review")
    st.title("JUOG 隔離認証・ACL接続確認")
    st.info("業務保存・復旧・メール送信は実装していません。")
    if not st.user.is_logged_in:
        if st.button("Googleでログイン"):
            st.login("google")
        st.stop()
    if not st.button("承認済み隔離先で自分のACLを確認"):
        st.stop()
    try:
        # _post checks enabled/release_approved/approved URL before signing or HTTP.
        # signed_request rejects missing/expired claims, including auth_time.
        result = _post(st, "ui_context",
                       {"id": "context", "action": "ui_context",
                        "payload": {"registration_id": ""}}, 30)
    except PermissionError:
        st.error("本人認証の条件を満たしていません。業務操作は停止しています。")
        st.stop()
    except Exception:
        st.error("ACL結果を確認できません。自動再送は行いません。")
        st.stop()
    roles = {"facility", "admin", "recovery_admin", "radiology",
             "medical_oncology", "urology"}
    valid = (isinstance(result, dict) and result.get("ok") is True
             and isinstance(result.get("user_id"), str)
             and bool(result["user_id"].strip())
             and result.get("role") in roles)
    if not valid:
        st.error("サーバー側の個人ACLを確認できません。業務操作は停止しています。")
        st.stop()
    if result["role"] == "facility":
        sites = result.get("facilities")
        if (not isinstance(sites, list) or not sites
                or any(not isinstance(site, str) or not site.strip() for site in sites)):
            st.error("施設権限を確認できません。業務操作は停止しています。")
            st.stop()
    # Do not echo identifiers, response payloads, tokens, secrets or exceptions.
    st.success("個人ACL応答の形式を確認しました。症例別認可・保存試験は未実施です。")
    # A context check is not authorization for a later request.
    # Every future read/write must independently recheck server ACL and ownership.
    st.stop()

if __name__ == "__main__":
    run()

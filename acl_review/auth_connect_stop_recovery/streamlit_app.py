"""Review candidate: AUTH_CONNECT recovery only. No business or boundary harness.
Not deployed. Reuses existing native OIDC, signed request, GAS ACL/session checks.
"""
import streamlit as st
from uat_auth_connect import context, context_envelope, send, valid_context

def run():
    st.set_page_config(page_title='JUOG AUTH_CONNECT',layout='centered')
    st.title('JUOG 隔離認証接続')
    st.info('AUTH_CONNECT：業務保存は禁止されています。')
    if not st.user.is_logged_in:
        if st.button('Googleでログイン'):
            st.login('google')
        st.stop()
    try:
        native=context(st)
    except Exception:
        st.error('本人認証・期限・設定を確認できません。送信していません。')
        st.stop()
    if st.button('現在の本人ACLを読取確認'):
        try:
            response=send(context_envelope(native))
            if not valid_context(response):
                raise PermissionError('ACL_NOT_CONFIRMED')
            st.success('TEST01・facility・AUTH_CONNECT・業務保存禁止を確認しました。')
        except Exception:
            st.error('ACLまたは接続を確認できません。再送していません。')
    st.caption('CRF入力画面はこの回復版には含みません。認証・ACLを迂回して開きません。')
    st.stop()

run()

"""Isolated entry: AUTH_CONNECT recovery only. No business or boundary harness.
Reuses existing native OIDC, signed request, GAS ACL/session checks.
"""
import time
import runpy
from pathlib import Path
import streamlit as st
from uat_auth_connect import context, context_envelope, send, valid_context
from auth_diagnostics import checked_context, ContextFailure, expired_native_login

def run():
    st.set_page_config(page_title='JUOG AUTH_CONNECT',layout='centered')
    st.title('JUOG 隔離認証接続')
    st.info('AUTH_CONNECT：業務保存は禁止されています。')
    if not st.user.is_logged_in:
        if st.button('Googleでログイン'):
            st.login('google')
        st.stop()
    if st.session_state.get('auth_connect_halted'):
        st.error('前回の異常で停止しています。管理者の確認が必要です。')
        st.caption('診断コード：'+st.session_state.get('_auth_failure_code','PREVIOUS_FAILURE_UNCLASSIFIED'))
        if expired_native_login(st.user,int(time.time())):
            if st.button('期限切れのログインを終了して再認証'):
                st.logout()
        st.stop()
    try:
        native=context(st)
    except Exception:
        st.error('本人認証・期限・設定を確認できません。送信していません。')
        iat, exp = st.user.get('iat'), st.user.get('exp')
        if type(iat) is int and type(exp) is int and int(time.time()) >= min(iat + 3600, exp):
            if st.button('期限切れのログインを終了して再認証'):
                st.logout()
        st.stop()
    inspect_crf = st.checkbox('30日CRFの画面確認（保存・取得・送信は無効）')
    if inspect_crf or st.button('現在の本人ACLを読取確認'):
        try:
            response=checked_context(send,context_envelope(native),valid_context)
            st.session_state['_canonical_acl_context'] = response
            st.success('TEST01・facility・AUTH_CONNECT・業務保存禁止を確認しました。')
        except Exception as error:
            st.session_state['_auth_failure_code'] = error.code if isinstance(error,ContextFailure) else 'LOCAL_CONTEXT_ERROR'
            st.session_state['_auth_failure_elapsed_ms'] = error.elapsed_ms if isinstance(error,ContextFailure) else None
            st.session_state['auth_connect_halted'] = True
            st.error('ACLまたは接続を確認できません。再送していません。')
            st.caption('診断コード：'+st.session_state['_auth_failure_code'])
            st.stop()
    if inspect_crf:
        st.warning('完全架空入力による画面確認専用です。台帳照合・保存・下書き取得・通知は実行できません。')
        if not st.session_state.get('_canonical_form_initialized'):
            for key in list(st.session_state):
                if str(key).startswith(('peri_', 'widget_peri_', 'draft30_')):
                    del st.session_state[key]
            st.session_state['_canonical_form_initialized'] = True
        runpy.run_path(str(Path(__file__).with_name('02_perioperative_30d_crf.py')), run_name='__main__')
    else:
        st.caption('30日CRFを表示する場合も、操作のたびに正規認証とGASの本人ACLを確認します。')
    st.stop()

run()

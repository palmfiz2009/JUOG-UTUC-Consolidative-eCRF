"""Existing fixture entry integration candidate; profile ships disabled."""
import runpy
import time
from pathlib import Path
import streamlit as st
from isolated_crf_adapter import call, context, begin_edit
from isolated_connection_feedback import connection_stop_message

def safe_logout():
    iat,exp=st.user.get('iat'),st.user.get('exp')
    if type(iat) is int and type(exp) is int and int(time.time())>=min(iat+3600,exp):
        st.logout();return
    r=call(st,'session_revoke',{})
    if r.get('ok') is not True or r.get('revoked') is not True:
        raise PermissionError('REVOCATION_UNCONFIRMED')
    st.logout()

def run():
    st.set_page_config(page_title='JUOG 隔離CRF統合候補',layout='wide')
    st.title('JUOG-UTUC01 隔離CRF')
    if not st.user.is_logged_in:
        st.session_state.pop('_connection_input_backup',None)
        if st.button('Googleでログイン'):st.login('google')
        st.stop()
    if st.button('セッションを失効してログアウト'):
        st.session_state.pop('_connection_input_backup',None)
        try:safe_logout()
        except Exception:st.error('失効を確認できません。停止を維持します。')
        st.stop()
    if st.session_state.get('auth_connect_halted'):
        st.session_state.pop('_connection_input_backup',None)
        st.error('認証・ACLの確認が必要です。保存を停止しています。');st.stop()
    try:context(st)
    except Exception as error:
        st.info(connection_stop_message(error, st));st.stop()
    r=call(st,'ui_context',{})
    if not (r.get('ok') is True and r.get('business_writes_allowed') is True):
        code=r.get('error')
        if code in {'RESULT_UNCONFIRMED','LOCK_TIMEOUT'}:
            # Fail closed for this run without treating a network timeout as
            # revoked identity. Keep widget data for a fresh signed ACL check.
            st.session_state['_connection_unconfirmed']=True
            from isolated_connection_state import preserve
            preserve(st.session_state)
            st.error('接続結果を確認できません。保存を停止しています。入力を保持して本人ACLを再確認してください。')
            if st.button('入力を保持して接続を再確認'):
                st.rerun()
            st.stop()
        st.session_state.pop('_connection_input_backup',None)
        st.session_state['auth_connect_halted']=True
        if code not in {'AUTH_EXPIRED','SESSION_REVOKED','ACL_DENIED','ACL_CHANGED','SESSION_STORE_FULL','SESSION_STORE_INVALID','RESULT_UNCONFIRMED','CONFIG_BINDING_MISMATCH','AUTHENTICATION_REQUIRED','LOCK_TIMEOUT'}:code='CONNECTION_UNCONFIRMED'
        st.error('本人ACLを確認できません。確認コード：'+code);st.stop()
    from isolated_connection_state import restore
    restore(st.session_state)
    st.session_state.pop('_connection_unconfirmed',None)
    st.caption('TEST01・完全架空データのみ。通知停止。B2はGoogleの直近再認証を保証しません。')
    if st.button('保存状態の照合・復旧を開く'):
        st.session_state['_show_recovery']=True
    if st.session_state.get('_show_recovery'):
        from isolated_recovery_ui import render
        render(st)
        if st.button('編集画面へ戻る'):
            st.session_state['_show_recovery']=False
            st.rerun()
        st.stop()
    subject=st.text_input('編集対象のJUOG登録番号',key='_integration_subject').strip().upper()
    if st.button('症例と現在のVersionを確認して編集開始'):
        checked=begin_edit(st,subject)
        if checked.get('ok') is not True:
            st.error('編集を開始できません。未確定保存・所有権・Versionを確認してください。');st.stop()
    if st.session_state.get('_integration_edit_subject')!=subject or not subject:
        st.info('編集対象を確認してください。');st.stop()
    pages={'30日':'02_perioperative_30d_crf.py','90日':'03_day90_crf.py','6〜24か月':'04_followup_crf.py'}
    page=st.selectbox('報告時点',list(pages),key='_integration_page')
    runpy.run_path(str(Path(__file__).with_name(pages[page])),run_name='__main__')

run()

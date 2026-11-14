"""AUTH_CONNECT-only UI. Native OIDC principal; never renders envelopes/secrets."""
import time
import urllib.request
import json
from types import SimpleNamespace
import streamlit as st
from uat_identity_proposal import identity_proposal
from uat_b2_auth_bridge import signed_request

URL='https://script.google.com/macros/s/AKfycbzLj9Dr-vUM6sTZHFOsxo0dUrscxNCp6LA196n2IBtYF3vYJ3ttnWLW3dY2eWJ7Gpf3GQ/exec'
GENERATION='d72bcf33-423d-4c4d-862d-2e2d69bc3edf'
FINGERPRINT='f0ea0ddb132e96bbd08cba4e37dc38609b73db5740530a05225c5acb6cab798f'

def context(st):
    cfg=dict(st.secrets['auth_connect'])
    if (cfg.get('enabled') is not True or cfg.get('review_approved') is not True or
            cfg.get('stage')!='AUTH_CONNECT' or cfg.get('url')!=URL or
            cfg.get('session_store_generation')!=GENERATION):
        raise PermissionError('CONFIG_NOT_APPROVED')
    client=st.secrets['auth']['google']['client_id']
    proposal=identity_proposal(st.user,client,int(time.time()))
    if proposal['principal_fingerprint']!=FINGERPRINT:
        raise PermissionError('PRINCIPAL_NOT_APPROVED')
    bridge=dict(oidc_issuer='https://accounts.google.com',oidc_client_id=client,
        signing_key=cfg['signing_key'],bridge_issuer='JUOG_ISOLATED_STREAMLIT_TEST01',
        audience='JUOG_AUTH04_GAS_TEST01',session_policy='isolated_gas_session_b2',
        session_environment='JUOG_AUTH04_ISOLATED_TEST01',session_store_generation=GENERATION,
        session_b_safety_review_approved=True,session_b_limited_execution_approved=True)
    return SimpleNamespace(user=st.user,secrets={'juog_identity_bridge':bridge})

def send(envelope):
    request=urllib.request.Request(URL,data=json.dumps(envelope).encode(),
        headers={'Content-Type':'application/json'},method='POST')
    with urllib.request.urlopen(request,timeout=30) as response:
        result=json.load(response)
    if not isinstance(result,dict):raise ValueError('INVALID_RESPONSE')
    return result

def context_envelope(native):
    return signed_request(native,'ui_context',{'id':'context','action':'ui_context','payload':{'registration_id':''}})

def valid_context(r):
    return (r.get('ok') is True and r.get('role')=='facility' and
        r.get('facilities')==['TEST01'] and r.get('facility_code')=='TEST01' and
        r.get('execution_stage')=='AUTH_CONNECT' and r.get('business_writes_allowed') is False)

def run():
    st.set_page_config(page_title='JUOG AUTH_CONNECT',layout='centered')
    st.title('JUOG 隔離認証接続試験')
    st.info('TEST01・本人1名。業務保存禁止。案BはGoogleでの直近1時間以内の再認証を保証しません。')
    if not st.user.is_logged_in:
        if st.button('Googleでログイン'):st.login('google')
        st.stop()
    if st.session_state.get('auth_connect_halted'):
        st.error('前回の異常で停止しています。管理者による確認・無効化が必要です。')
        st.stop()
    from uat_boundary_probe import panel as boundary_panel
    boundary_panel(lambda:context(st), context_envelope, send, valid_context)
    probe=st.session_state.get('real_boundary_probe', {})
    if st.session_state.get('auth_connect_halted') or probe.get('phase') in ('WAITING','WAITING_EXPIRY','CHECKING_EXPIRY'):
        st.stop()
    try:native=context(st)
    except Exception:
        st.error('承認条件・本人認証・期限・設定を確認できません。接続していません。')
        iat, exp = st.user.get('iat'), st.user.get('exp')
        if type(iat) is int and type(exp) is int and int(time.time()) >= min(iat + 3600, exp):
            if st.button('期限切れのログインを終了して再認証'):st.logout()
        st.stop()
    if st.session_state.get('auth_connect_halted'):
        st.error('前回の異常で接続試験を停止しています。管理者による確認・無効化が必要です。')
        st.stop()
    if st.button('現在の本人ACLを1回だけ照合'):
        try:
            result=send(context_envelope(native))
            if valid_context(result):st.success('ACL_SINGLE_ALLOWED_TEST01_FACILITY')
            elif result.get('ok') is False and result.get('error') == 'ACL_DENIED':
                st.warning('ACL_SINGLE_DENIED：'+result['error'])
            elif result.get('ok') is False and result.get('error') == 'UNIFIED_TRANSACTION_INCOMPLETE':
                st.error('ACL_SINGLE_REJECTED_UNCLASSIFIED：UNIFIED_TRANSACTION_INCOMPLETE（ACL合格には加算しません）')
                st.session_state['auth_connect_halted']=True
                st.stop()
            else:raise PermissionError('UNEXPECTED_RESPONSE')
        except Exception:
            st.session_state['auth_connect_halted']=True
            st.error('単回ACL照合を確認できません。自動再送しません。')
            st.stop()
    if st.button('本人ACLと拒否条件を実測'):
        checks=[]
        def record(name, passed):
            checks.append((name,passed))
            if not passed:raise PermissionError('UNEXPECTED_RESPONSE')
        try:
            r=send({});record('未認証拒否',r.get('ok') is False and r.get('error')=='AUTH_REQUIRED')
            e=context_envelope(native);a=e['identity_assertion'];e['identity_assertion']=a[:-6]+'AAAAAA'
            r=send(e);record('不正署名拒否',r.get('ok') is False and r.get('error')=='AUTH_INVALID')
            e=context_envelope(native);r=send(e);record('本人TEST01許可',valid_context(r))
            if not checks[-1][1]:raise PermissionError('CONTEXT_FAILED')
            r=send(e);record('同一署名再利用拒否',r.get('ok') is False and r.get('error')=='ASSERTION_REPLAY')
            r=send(signed_request(native,'save_crf',{'id':'deny-save','action':'save_crf','payload':{}}))
            record('業務保存拒否',r.get('ok') is False and r.get('error')=='AUTH04_EXECUTION_NOT_APPROVED')
            e=context_envelope(native);time.sleep(16);r=send(e)
            record('15秒署名の期限切れ拒否',r.get('ok') is False and r.get('error')=='AUTH_EXPIRED')
            st.table([{'項目':n,'結果':'確認済み' if passed else '不一致・停止'} for n,passed in checks])
            if not all(p for _,p in checks):st.error('不一致があります。試験を停止して管理者が無効化してください。')
            else:st.success('認証接続試験の応答を確認しました。業務台帳・監査の別途照合が必要です。')
        except Exception:
            st.session_state['auth_connect_halted']=True
            st.error('通信または検証が完了しませんでした。自動再送しません。管理者が無効化して確認してください。')
            st.stop()
    if st.button('セッション失効と再利用拒否を確認してログアウト'):
        try:
            pending=context_envelope(native)
            r=send(signed_request(native,'session_revoke',{}))
            if r.get('ok') is not True or r.get('revoked') is not True:raise PermissionError('REVOKE_FAILED')
            r=send(pending)
            if r.get('ok') is not False or r.get('error')!='SESSION_REVOKED':raise PermissionError('REVOKE_NOT_ENFORCED')
            st.success('失効の確定と発行済み署名の拒否を確認しました。')
            st.logout()
        except Exception:
            st.session_state['auth_connect_halted']=True
            st.error('失効または再利用拒否を確認できません。通信遅延による署名期限切れも含みます。自動再送せず管理者が確認してください。')
            st.stop()
    st.caption('トークン・本人識別子・署名・秘密値は表示しません。正式UAT判定は証拠照合後です。')
    st.stop()

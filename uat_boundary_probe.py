"""Real-clock observation only; no altered token timestamps, ACL, or business APIs."""
import time
import base64, json
import streamlit as st

def token_identity(user):
    import hashlib, json
    # Retain a digest only, never raw principal/nonce/token evidence.
    material=[user.get(k) for k in ('iss','sub','aud','azp','iat','exp','nonce')]
    return hashlib.sha256(json.dumps(material,sort_keys=True,separators=(',', ':')).encode()).hexdigest()

def advance(state, now, user, get_context, make_envelope, send, valid_context):
    if state['phase'] in ('DONE','FAILED'):return
    if (not user.is_logged_in or token_identity(user)!=state['token_identity'] or now<state.get('last_now',state['started'])):
        state.pop('pending_envelope',None)
        state.update(phase='FAILED',reason='認証結果または時計が変化しました。境界試験は未完了です。');return
    state['last_now']=now
    deadline=state['deadline'];left=deadline-now
    try:
        if 0<left<=25 and not state.get('before_attempted'):
            state['before_attempted']=True
            native=get_context()
            before_envelope=make_envelope(native)
            encoded=before_envelope['identity_assertion'].split('.')[0]
            before_claims=json.loads(base64.urlsafe_b64decode(encoded+'='*(-len(encoded)%4)))
            state['before_sid']=before_claims['session']['sid']
            state['before_generation']=before_claims['session']['generation']
            state['before_ok']=valid_context(send(before_envelope))
            state['before_seconds_left']=deadline-int(time.time())
            if not state['before_ok'] or state['before_seconds_left']<=0:raise PermissionError('PREBOUNDARY_NOT_CONFIRMED')
            state['phase']='WAITING_EXPIRY'
        # Network latency may have consumed part of the pre-boundary window.
        actual_now=int(time.time());left=deadline-actual_now
        if actual_now<now:raise PermissionError('CLOCK_CHANGED')
        if 0<left<=10 and state.get('before_ok') and not state.get('pending_generated'):
            state['pending_generated']=True
            envelope=make_envelope(get_context())
            encoded=envelope['identity_assertion'].split('.')[0]
            claims=json.loads(base64.urlsafe_b64decode(encoded+'='*(-len(encoded)%4)))
            session=claims.get('session',{});generated_at=int(time.time())
            if (claims.get('v')!=2 or type(claims.get('exp')) is not int or claims.get('exp')!=deadline or
                type(claims.get('iat')) is not int or not deadline-10<=claims['iat']<deadline or
                claims['iat']>generated_at or generated_at>=deadline or generated_at<actual_now or
                session.get('sid')!=state['before_sid'] or session.get('generation')!=state['before_generation'] or
                session.get('deadline')!=deadline or
                session.get('token_iat')!=user.get('iat')):
                raise PermissionError('PENDING_DEADLINE_NOT_CONFIRMED')
            state['pending_envelope']=envelope
            state['pending_seconds_left']=deadline-generated_at
        if left<=0:
            if not state.get('before_ok') or actual_now-deadline>20 or state['duration']!=3600:raise PermissionError('BOUNDARY_NOT_OBSERVED')
            state['phase']='CHECKING_EXPIRY'
            try:
                native=get_context();make_envelope(native)
            except PermissionError as exc:
                if str(exc) not in ('RELOGIN_REQUIRED','APP_SESSION_EXPIRED','OIDC_TOKEN_EXPIRED_OR_MISSING'):raise
                state['signer_denied']=True
            else:raise PermissionError('SIGNER_ALLOWED_EXPIRED_SESSION')
            pending=state.pop('pending_envelope',None)
            if pending is None or state.get('pending_sent'):
                raise PermissionError('PENDING_BOUNDARY_NOT_OBSERVED')
            state['pending_sent']=True
            reply=send(pending)
            state['gas_expired_denied']=reply.get('ok') is False and reply.get('error')=='AUTH_EXPIRED'
            if not state['gas_expired_denied']:
                raise PermissionError('GAS_EXPIRY_NOT_CONFIRMED')
            state['cookie_still_present']=bool(user.is_logged_in)
            state['observed_elapsed']=int(time.time())-state['started']
            state['phase']='DONE'
    except Exception:
        state.pop('pending_envelope',None)
        state.update(phase='FAILED',reason='期限境界の通信・応答を確認できません。自動再送せず管理者が確認してください。')

@st.fragment(run_every=5)
def panel(get_context, make_envelope, send, valid_context):
    if st.session_state.get('auth_connect_halted'):
        st.error('異常停止中のため境界試験を実行しません。');return
    st.subheader('60分セッション境界：実時間観測')
    now=int(time.time());iat,exp=st.user.get('iat'),st.user.get('exp')
    if type(iat) is not int or type(exp) is not int:
        st.warning('認証時刻属性を確認できません。');return
    deadline=min(iat+3600,exp)
    st.write('現在の認証結果の上限まで：'+str(max(0,deadline-now))+'秒')
    st.caption('時計・認証時刻・期限は変更しません。画面を開いた状態で期限直前と到達後を観測します。再読込で観測表示はリセットされても、認証期限は延長されません。')
    state=st.session_state.get('real_boundary_probe')
    if exp < iat+3600:
        st.warning('トークン期限が60分より短いため60分境界試験には使用しません。');return
    if state is None:
        if st.button('実時間境界の観測を開始'):
            try:
                if deadline-now<40:raise PermissionError('TOO_LATE')
                native=get_context()
                if not valid_context(send(make_envelope(native))):raise PermissionError('START_DENIED')
                state=dict(phase='WAITING',started=now,deadline=deadline,token_identity=token_identity(st.user),duration=deadline-iat,last_now=now)
                st.session_state['real_boundary_probe']=state
            except Exception:
                st.error('観測を開始できません。設定変更・自動再送は行いません。')
                st.session_state['auth_connect_halted']=True
        return
    advance(state,now,st.user,get_context,make_envelope,send,valid_context)
    st.write('観測状態：'+state['phase'])
    if state['phase']=='DONE':
        st.table([{'確認項目':n,'結果':'確認済み' if v else '未確認'} for n,v in [
            ('期限直前のGAS許可',state.get('before_ok')),
            ('期限後のPython署名拒否',state.get('signer_denied')),
            ('同一期限の発行済み署名をGASが拒否',state.get('gas_expired_denied')),
            ('既存Cookieが残っていても期限後拒否',state.get('cookie_still_present'))]])
        st.write('観測開始からの実経過：'+str(state['observed_elapsed'])+'秒')
        st.write('期限直前の応答受信時の残り時間：'+str(state['before_seconds_left'])+'秒')
        st.caption('同じ認証結果のiatから60分でPythonが署名を停止する証拠です。発行済み署名は同じ期限に制限し、期限後に1回だけ送信しています。署名とセッションの期限が一致する試験であり、GAS側60分制限だけを独立に証明するものではありません。正式UAT加算は証拠照合後です。')
    elif state['phase']=='FAILED':
        st.session_state['auth_connect_halted']=True
        st.error(state['reason'])

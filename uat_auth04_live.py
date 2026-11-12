"""Isolated AUTH04 harness. Disabled unless exact reviewed config is supplied.
No legacy navigation, arbitrary payload editor, raw responses or secret output.
"""
import copy, hashlib, json, time, uuid, urllib.error
from pathlib import Path
from types import SimpleNamespace
import streamlit as st
from uat_auth_connect import URL, GENERATION, FINGERPRINT, send
from uat_identity_proposal import identity_proposal
from auth04_config import load_config
from uat_b2_auth_bridge import signed_request
from juog_common import capture_draft_state, restore_draft_state, clear_session_state_prefixes
CASE='JUOG-970'; FACILITY='TEST01'
FIXTURE_PATH=Path(__file__).with_name('uat_auth04_fixture.json')
FIXTURE_SHA=hashlib.sha256(FIXTURE_PATH.read_bytes()).hexdigest()
WRITE_ACTIONS={'save_draft','save_crf'}
READ_ACTIONS={'ui_context','get_draft','read_crf'}
LIFECYCLE={'prepare_request','execute_request','request_status'}
PREPARE_MIN_REMAINING_SECONDS=900

class PrepareWindowClosed(PermissionError):
    """Local refusal before transmission; does not imply an uncertain write."""

def require_prepare_window(native):
    # Called only after native_context validates the OIDC result. This additional
    # experiment limit never changes the authentication deadline.
    now=int(time.time());iat,exp=native.user.get('iat'),native.user.get('exp')
    if (type(iat) is not int or type(exp) is not int or not 0<=iat<=now<exp or
        min(iat+3600,exp)-now<PREPARE_MIN_REMAINING_SECONDS):
        raise PrepareWindowClosed('AUTH04_PREPARE_WINDOW_CLOSED')
PAIRS={('perioperative_30d','30d'),('day90','90d'),('followup','6m')}
PRIVACY_FIXTURES=[{'reg_birth_date': 'SYNTHETIC-ID'}, {'regBirthDate': 'SYNTHETIC-ID'}, {'regFirstName': 'SYNTHETIC-ID'}, {'regLastName': 'SYNTHETIC-ID'}, {'regDOB': 'SYNTHETIC-ID'}, {'regＭＲＮ': 'SYNTHETIC-ID'}, {'regＢirthDate': 'SYNTHETIC-ID'}, {'note': '患者氏名は架空検証者'}, {'note': 'カルテ番号はSYNTHETIC-001'}, {'note': '生年月日は１９８０年１月２日'}, {'note': 'DOB: 1980-01-02'}, {'nested': [{'encoded': '{"regFirstName": "FICTIONAL"}'}]}, {'患者氏名': 'SYNTHETIC-ID'}, {'カルテ番号': 'SYNTHETIC-ID'}, {'生年月日': '1980-01-02'}, {'nested': [{'encoded': '{"患者氏名": "SYNTHETIC-ID"}'}]}]

def native_context(ui):
    cfg=load_config();auth=dict(ui.secrets['auth_connect'])
    if (cfg.get('enabled') is not True or cfg.get('stage')!='AUTH04_APPROVED' or
        cfg.get('fixture_id')!=CASE or cfg.get('facility_code')!=FACILITY or
        cfg.get('fixture_sha256')!=FIXTURE_SHA or cfg.get('url')!=URL or
        not cfg.get('approval_ref') or not cfg.get('review_ref') or
        cfg.get('prerequisites_verified') is not True or cfg.get('notifications_disabled') is not True or
        cfg.get('session_store_generation')!=GENERATION or
        set(cfg.get('write_actions',[]))!=WRITE_ACTIONS):
        raise PermissionError('AUTH04_PREREQUISITES_NOT_VERIFIED')
    client=ui.secrets['auth']['google']['client_id']
    if identity_proposal(ui.user,client,int(time.time()))['principal_fingerprint']!=FINGERPRINT:
        raise PermissionError('PRINCIPAL_NOT_APPROVED')
    bridge=dict(oidc_issuer='https://accounts.google.com',oidc_client_id=client,
        signing_key=auth['signing_key'],bridge_issuer='JUOG_ISOLATED_STREAMLIT_TEST01',
        audience='JUOG_AUTH04_GAS_TEST01',session_policy='isolated_gas_session_b2',
        session_environment='JUOG_AUTH04_ISOLATED_TEST01',session_store_generation=GENERATION,
        session_b_safety_review_approved=True,session_b_limited_execution_approved=True)
    return SimpleNamespace(user=ui.user,secrets={'juog_identity_bridge':bridge})

def check_payload(action,payload):
    if action not in WRITE_ACTIONS|READ_ACTIONS:raise PermissionError('ACTION_NOT_ALLOWED')
    if payload.get('registration_id')!=CASE:raise PermissionError('CASE_NOT_ALLOWED')
    if payload.get('facility_code',FACILITY)!=FACILITY:raise PermissionError('FACILITY_NOT_ALLOWED')
    if action!='ui_context' and (payload.get('crf_type'),payload.get('visit')) not in PAIRS:
        raise PermissionError('CRF_NOT_ALLOWED')
    key=payload.get('record_key')
    if key is not None and key!='|'.join([CASE,payload['crf_type'],payload['visit']]):
        raise PermissionError('RECORD_NOT_ALLOWED')
    if any(k in payload for k in ('actor','user_id','subject','issuer','role')):
        raise PermissionError('ACTOR_OVERRIDE_FORBIDDEN')

def call(ui,action,payload):
    if action not in READ_ACTIONS|LIFECYCLE:raise PermissionError('ACTION_NOT_ALLOWED')
    if action=='prepare_request':
        if payload.get('action') not in WRITE_ACTIONS:raise PermissionError('WRITE_NOT_ALLOWED')
        check_payload(payload['action'],payload.get('payload',{}));body=payload
    elif action in ('execute_request','request_status'):
        if set(payload)!={'operation_id'} or payload['operation_id'] not in ui.session_state.get('auth04_operation_ids',[]):
            raise PermissionError('OPERATION_NOT_OBSERVED')
        body=payload
    else:
        check_payload(action,payload)
        outbound=copy.deepcopy(payload)
        if action=='ui_context':outbound={'registration_id':payload['registration_id']}
        if action=='read_crf':outbound={k:payload[k] for k in ('registration_id','facility_code','record_key')}
        body={'id':'auth04_read_'+uuid.uuid4().hex,'action':action,'payload':outbound}
    native=native_context(ui)
    if action=='prepare_request':require_prepare_window(native)
    envelope=signed_request(native,action,body)
    if action=='prepare_request':require_prepare_window(native)
    return send(envelope)

def context(ui):
    r=call(ui,'ui_context',{'registration_id':CASE,'facility_code':FACILITY})
    if not (r.get('ok') is True and r.get('role')=='facility' and r.get('facilities')==[FACILITY] and r.get('facility_code')==FACILITY and r.get('isolation') is True and type(r.get('revision')) is int):
        raise PermissionError('AUTH04_CONTEXT_NOT_VERIFIED')
    return r

def write_once(ui,action,payload):
    if ui.session_state.get('auth04_pending') or ui.session_state.get('auth04_preparation_uncertain'):
        raise PermissionError('RECONCILE_BEFORE_NEW_PREPARE')
    context(ui)
    ui.session_state['auth04_preparation_uncertain']=True
    try:prepared=call(ui,'prepare_request',{'action':action,'payload':payload})
    except PrepareWindowClosed:
        ui.session_state['auth04_preparation_uncertain']=False
        raise
    if prepared.get('state')=='UNKNOWN' or prepared.get('error') in ('PREPARATION_UNCERTAIN','REQUEST_UNCERTAIN_RECONCILE_BEFORE_RETRY'):
        raise PermissionError('PREPARATION_UNCERTAIN')
    ui.session_state['auth04_preparation_uncertain']=False
    if prepared.get('ok') is not True:return prepared
    op=prepared.get('operation_id')
    if not isinstance(op,str) or not op:raise PermissionError('INVALID_OPERATION_ID')
    ui.session_state.setdefault('auth04_operation_ids',[]).append(op)
    ui.session_state['auth04_pending']=op
    result=call(ui,'execute_request',{'operation_id':op})
    record_execution_diagnostic(ui,'EXECUTE',result)
    status=call(ui,'request_status',{'operation_id':op})
    record_execution_diagnostic(ui,'STATUS',status)
    if status.get('ok') is True and status.get('state') in ('SAVED','FAILED'):
        ui.session_state['auth04_pending']=None
    if result.get('ok') is True and (result.get('state')!='SAVED' or status.get('state')!='SAVED'):
        raise PermissionError('SAVE_NOT_CONFIRMED')
    if result.get('ok') is True and status.get('state')=='SAVED':
        ui.session_state['auth04_last_saved_operation']=op
    return result

def crf_payload(index,version=1):
    p=copy.deepcopy(json.loads(FIXTURE_PATH.read_text())['crfs'][index])
    if version==2:
        p.update(submission_id=p['submission_id'].replace('-V1','-V2'),submission_kind='訂正報告',expected_record_version=1,correction_reason='完全架空UATの訂正確認')
    return p

def draft_payload():
    return dict(registration_id=CASE,facility_code=FACILITY,facility_name='完全架空施設',crf_type='perioperative_30d',visit='30d',reporter_email='fictional@example.invalid',draft_state={
        'peri_age':{'type':'value','value':46},'peri_birth_year_month':{'type':'value','value':'1980-01'},'peri_day30_visit_date':{'type':'date','value':'2026-05-13'},'peri_clinical_note':{'type':'value','value':'完全架空の臨床記載'}})

def read_payload(index=0):
    p=crf_payload(index)
    return {k:p[k] for k in ('registration_id','facility_code','crf_type','visit','record_key','reporter_email')}

def read_records(ui,index=0):
    r=call(ui,'read_crf',read_payload(index))
    if r.get('ok') is not True:raise PermissionError('READ_NOT_CONFIRMED')
    records=r.get('result',{}).get('records')
    if not isinstance(records,list):raise PermissionError('INVALID_RECORDS')
    expected_key=crf_payload(index)['record_key']
    if any(x.get('record_key')!=expected_key or x.get('payload',{}).get('registration_id')!=CASE for x in records):raise PermissionError('WRONG_RECORDS')
    return r,records

def linked_crf_payload(ui,index,version=1):
    p=crf_payload(index,version)
    if index:
        _,records=read_records(ui,0)
        if not records:raise PermissionError('SOURCE_30D_REQUIRED')
        latest=max(records,key=lambda x:x.get('record_version',0))
        if type(latest.get('record_version')) is not int or not latest.get('submission_id'):raise PermissionError('INVALID_SOURCE_30D')
        p['data']['source_30d_record_version']=latest['record_version']
        p['data']['source_30d_submission_id']=latest['submission_id']
    return p

def verify_history(ui,index):
    r,records=read_records(ui,index)
    expected_count=ui.session_state.get('auth04_expected_versions',{}).get(index)
    if expected_count is None:raise PermissionError('NO_SAVED_EXPECTATION')
    if sorted(x.get('record_version') for x in records)!=list(range(1,expected_count+1)):raise PermissionError('VERSION_MISMATCH')
    expected=ui.session_state.get('auth04_expected_payloads',{})
    for rec in records:
        p=expected.get(str(index)+':'+str(rec['record_version']))
        if p is None or any(rec['payload'].get(k)!=v for k,v in p.items()):raise PermissionError('PAYLOAD_MISMATCH')
    first=next(x for x in records if x['record_version']==1)
    digest=hashlib.sha256(json.dumps(first,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    old=ui.session_state.setdefault('auth04_v1_hashes',{}).setdefault(index,digest)
    if old!=digest:raise PermissionError('OLD_VERSION_CHANGED')
    return r

def save_expected_crf(ui,index,version):
    if version==2 and (ui.session_state.get('auth04_expected_versions',{}).get(index)!=1 or index not in ui.session_state.get('auth04_v1_hashes',{})):
        raise PermissionError('BASE_VERSION_NOT_OBSERVED')
    if ui.session_state.get('auth04_expected_versions',{}).get(index,0)>=version:
        raise PermissionError('USE_EXISTING_OPERATION_FOR_REPLAY')
    p=linked_crf_payload(ui,index,version);r=write_once(ui,'save_crf',p)
    if r.get('ok') is not True or r.get('state')!='SAVED':raise PermissionError('NORMAL_SAVE_FAILED')
    ui.session_state.setdefault('auth04_expected_versions',{})[index]=version
    ui.session_state.setdefault('auth04_expected_payloads',{})[str(index)+':'+str(version)]=p
    verify_history(ui,index)
    return r

def resume_observed_90d(ui):
    """Explicit recovery of this supervised run's observed unfinished 90d v1.
    No new preparation, arbitrary operation ID, or automatic retry is available.
    """
    op=ui.session_state.get('auth04_pending')
    if (not isinstance(op,str) or not op or op not in ui.session_state.get('auth04_operation_ids',[]) or
        ui.session_state.get('auth04_preparation_uncertain') or
        ui.session_state.get('auth04_expected_versions',{}).get(0)!=2 or
        ui.session_state.get('auth04_expected_versions',{}).get(1) is not None):
        raise PermissionError('RECOVERY_CONTEXT_NOT_VERIFIED')
    ui.session_state['auth04_halted']=True
    expected=linked_crf_payload(ui,1,1)
    if expected.get('data',{}).get('source_30d_record_version')!=2:
        raise PermissionError('RECOVERY_SOURCE_VERSION_CHANGED')
    status=call(ui,'request_status',{'operation_id':op})
    record_execution_diagnostic(ui,'RECOVERY_STATUS',status)
    if status.get('ok') is not True or status.get('action')!='save_crf' or status.get('state') not in ('UNFINISHED','SAVED'):
        raise PermissionError('RECOVERY_STATUS_NOT_VERIFIED')
    if status['state']=='UNFINISHED':
        if status.get('phase')!='AUDIT_OR_COMMIT_PENDING':
            raise PermissionError('RECOVERY_INTENT_NOT_VERIFIED')
        result=call(ui,'execute_request',{'operation_id':op})
        record_execution_diagnostic(ui,'RECOVERY_EXECUTE',result)
        status=call(ui,'request_status',{'operation_id':op})
        record_execution_diagnostic(ui,'RECOVERY_STATUS',status)
    if status.get('ok') is not True or status.get('state')!='SAVED' or status.get('action')!='save_crf':
        raise PermissionError('RECOVERY_SAVE_NOT_CONFIRMED')
    r,records=read_records(ui,1)
    if len(records)!=1 or records[0].get('record_version')!=1 or records[0].get('payload')!=expected:
        raise PermissionError('RECOVERY_PAYLOAD_MISMATCH')
    old_versions=copy.deepcopy(ui.session_state.get('auth04_expected_versions',{}))
    old_payloads=copy.deepcopy(ui.session_state.get('auth04_expected_payloads',{}))
    old_hashes=copy.deepcopy(ui.session_state.get('auth04_v1_hashes',{}))
    ui.session_state.setdefault('auth04_expected_versions',{})[1]=1
    ui.session_state.setdefault('auth04_expected_payloads',{})['1:1']=expected
    try:verify_history(ui,1)
    except Exception:
        ui.session_state['auth04_expected_versions']=old_versions
        ui.session_state['auth04_expected_payloads']=old_payloads
        ui.session_state['auth04_v1_hashes']=old_hashes
        raise
    ui.session_state['auth04_pending']=None
    ui.session_state['auth04_last_saved_operation']=op
    ui.session_state['auth04_halted']=False
    ui.session_state.pop('auth04_last_exception_category',None)
    ui.session_state.setdefault('auth04_results',[]).append({'check':'90日CRF同一操作の復旧・読取照合',**summarize(status)})
    return status

def semantic_json_strings(value):
    if isinstance(value,str) and value.lstrip().startswith(('{','[')):
        try:return semantic_json_strings(json.loads(value))
        except (ValueError,TypeError):return value
    if isinstance(value,dict):return {k:semantic_json_strings(v) for k,v in value.items()}
    if isinstance(value,list):return [semantic_json_strings(v) for v in value]
    return value

def expected_legacy90d():
    return {'d90_age':{'type':'value','value':46},'d90_birth_year_month':{'type':'value','value':'1980-01'},'d90_clinical_note':{'type':'value','value':'完全架空の臨床記載'},'d90_nested':{'type':'value','value':'{"CRP":0}'}}

def legacy90d_matches(draft,expected):
    # JSON-string whitespace may differ; string-to-object coercion and numeric
    # type drift must not be concealed by semantic JSON comparison.
    if type(draft) is not dict or set(draft)!=set(expected):return False
    for key,want in expected.items():
        got=draft[key]
        if (type(got) is not dict or set(got)!=set(want) or
            type(got.get('type')) is not str or got['type']!=want['type'] or
            type(got.get('value')) is not type(want['value'])):return False
    return semantic_json_strings(draft)==semantic_json_strings(expected)

def legacy90d_read_restore(ui):
    r=call(ui,'get_draft',read_payload(1));result=r.get('result',{})
    if r.get('ok') is not True or result.get('source_found') is not True:raise PermissionError('LEGACY_READ_NOT_CONFIRMED')
    draft=result.get('draft_state');expected=expected_legacy90d()
    # Compare the server return before local redaction can conceal a server defect.
    if not legacy90d_matches(draft,expected):raise PermissionError('SERVER_LEGACY_REDACTION_MISMATCH')
    ui.session_state['d90_patient_name']='SYNTHETIC-STALE';ui.session_state['widget_d90_patient_name']='SYNTHETIC-STALE'
    clear_session_state_prefixes(('d90_','widget_d90_'));restore_draft_state(draft)
    if 'd90_patient_name' in ui.session_state or 'widget_d90_patient_name' in ui.session_state or not legacy90d_matches(capture_draft_state('d90_'),expected):raise PermissionError('LEGACY_RESTORE_MISMATCH')
    return r

def other_owner_read_denied(ui):
    r=call(ui,'get_draft',read_payload(2))
    if r.get('ok') is not False or r.get('error')!='DRAFT_OWNER_REQUIRED':raise PermissionError('OWNER_REJECTION_NOT_CONFIRMED')
    return r

def summarize(result):
    # Never render raw result, error message/details, actor, data, or operation ID.
    known={'DIRECT_IDENTIFIER_NOT_ALLOWED','ACL_DENIED','DRAFT_OWNER_REQUIRED','STALE_VERSION','CORRECTION_REASON_REQUIRED','INITIAL_ALREADY_EXISTS','NO_PRIOR_RECORD','VALIDATION_FAILED','REQUEST_NOT_VISIBLE','STATUS_UNVERIFIABLE','AUTH_EXPIRED','SESSION_REVOKED','AUTH_REQUIRED','UNIFIED_TRANSACTION_INCOMPLETE','UNFINISHED_REQUEST_BLOCKS_NEW_OPERATION','UNKNOWN_REQUEST_BLOCKS_NEW_OPERATION','AUTH_INVALID','SESSION_INVALID','SESSION_STORE_INVALID','SESSION_STORE_UNAVAILABLE','ASSERTION_REPLAY','LOCK_TIMEOUT','PREPARATION_UNCERTAIN','AUTH04_SCOPE_DENIED','AUTH04_SCOPE_NOT_APPROVED','AUTH04_EXECUTION_NOT_APPROVED','DOMAIN_INCOMPLETE','DOMAIN_RECOVERY_REQUIRED','EXECUTION_UNCERTAIN','RECONCILIATION_REQUIRED','AUDIT_NOT_CONFIRMED'}
    error=result.get('error');state=result.get('state')
    return {'ok':result.get('ok') is True,'state':state if isinstance(state,str) and state in ('SAVED','FAILED','UNKNOWN','UNFINISHED') else None,'error':error if isinstance(error,str) and error in known else ('UNCLASSIFIED' if error else None)}

def record_execution_diagnostic(ui,phase,result):
    if phase not in ('EXECUTE','STATUS','RECOVERY_EXECUTE','RECOVERY_STATUS'):raise ValueError('DIAGNOSTIC_PHASE')
    ui.session_state.setdefault('auth04_execution_diagnostics',[]).append({'phase':phase,**summarize(result)})

def safe_exception_category(exc):
    # Classify without formatting exception messages, URLs, bodies or arguments.
    if isinstance(exc,TimeoutError):return 'TIMEOUT'
    if isinstance(exc,urllib.error.HTTPError):return 'HTTP_ERROR'
    if isinstance(exc,urllib.error.URLError):
        return 'TIMEOUT' if isinstance(exc.reason,TimeoutError) else 'TRANSPORT_ERROR'
    if isinstance(exc,json.JSONDecodeError):return 'INVALID_JSON'
    return 'LOCAL_CHECK_FAILED'

def elapsed_bucket(start):
    seconds=max(0,time.monotonic()-start)
    return 'LT_15S' if seconds<15 else ('15_TO_30S' if seconds<30 else 'GE_30S')

def privacy_probe_once(ui):
    # One fixed fixture per explicit click. Unknown requests are never retried.
    if any(ui.session_state.get(k) for k in ('auth04_halted','auth04_preparation_uncertain','auth04_pending')):
        raise PermissionError('RECONCILE_BEFORE_NEW_PREPARE')
    index=ui.session_state.get('auth04_privacy_next',0)
    if type(index) is not int or not 0<=index<len(PRIVACY_FIXTURES):
        raise PermissionError('PRIVACY_SEQUENCE_NOT_AVAILABLE')
    row={'fixture':index+1,'confirmed':False,'category':'REQUEST_STARTED'}
    ui.session_state.setdefault('auth04_privacy_progress',[]).append(row)
    p=draft_payload();p['draft_state']['privacy_probe']=copy.deepcopy(PRIVACY_FIXTURES[index])
    ui.session_state['auth04_preparation_uncertain']=True
    started=time.monotonic()
    try:r=call(ui,'prepare_request',{'action':'save_draft','payload':p})
    except PrepareWindowClosed:
        row['category']='LOCAL_WINDOW_CLOSED';ui.session_state['auth04_preparation_uncertain']=False
        raise
    except Exception as exc:
        row['category']=safe_exception_category(exc);ui.session_state['auth04_halted']=True
        raise
    finally:row['elapsed']=elapsed_bucket(started)
    safe=summarize(r);row.update(safe);row['category']='RESPONSE_RECEIVED'
    if r.get('ok') is not False or r.get('error')!='DIRECT_IDENTIFIER_NOT_ALLOWED':
        op=r.get('operation_id')
        if isinstance(op,str) and op:
            ui.session_state.setdefault('auth04_operation_ids',[]).append(op);ui.session_state['auth04_pending']=op
        ui.session_state['auth04_halted']=True
        raise PermissionError('PRIVACY_REJECTION_NOT_CONFIRMED')
    row['confirmed']=True;ui.session_state['auth04_privacy_next']=index+1
    ui.session_state['auth04_preparation_uncertain']=False
    return r

def render_progress(ui):
    if ui.session_state.get('auth04_results'):ui.table(ui.session_state['auth04_results'])
    if ui.session_state.get('auth04_privacy_progress'):ui.table(ui.session_state['auth04_privacy_progress'])
    if ui.session_state.get('auth04_execution_diagnostics'):ui.table(ui.session_state['auth04_execution_diagnostics'])
    if ui.session_state.get('auth04_last_exception_category'):ui.caption(ui.session_state['auth04_last_exception_category'])

def run():
    st.set_page_config(page_title='JUOG AUTH04 isolated',layout='centered')
    st.title('AUTH-04 隔離実機試験')
    st.caption('TEST01・JUOG-970・完全架空データ限定。生の応答・識別入力・本人識別子は表示しません。')
    if not st.user.is_logged_in:
        if st.button('Googleでログイン'):st.login('google')
        st.stop()
    try:native_context(st)
    except Exception:
        st.error('AUTH-04の承認・安全性・対象設定を確認できません。送信していません。')
        iat,exp=st.user.get('iat'),st.user.get('exp')
        if type(iat) is int and type(exp) is int and int(time.time())>=min(iat+3600,exp):
            if st.button('期限切れのログインを終了して再認証'):st.logout()
        st.stop()
    render_progress(st)
    if st.session_state.get('auth04_preparation_uncertain'):
        st.error('応答が不確定なため停止しています。新しいprepareを送らず、サーバー台帳を照合してください。');st.stop()
    pending=st.session_state.get('auth04_pending')
    if pending:
        if st.button('保存状態を照合'):
            try:
                r=call(st,'request_status',{'operation_id':pending});st.json(summarize(r))
                record_execution_diagnostic(st,'RECOVERY_STATUS',r)
            except Exception:st.error('状態不明。新しい要求は送信しません。')
        if st.button('未完了の90日CRFを同じ操作IDで一度だけ再開'):
            try:
                resume_observed_90d(st)
                st.success('90日CRFの保存・読取照合が完了しました。次の操作は画面の再実行後に選択できます。')
            except Exception as exc:
                st.session_state['auth04_halted']=True
                st.session_state['auth04_last_exception_category']=safe_exception_category(exc)
                st.error('復旧を確認できないため停止しました。新規prepare・自動再送はしません。')
            render_progress(st)
        st.stop()
    if st.session_state.get('auth04_halted'):
        st.error('検証不一致により停止中です。サーバー台帳を照合してください。');st.stop()
    choices=['接続・対象症例確認','識別入力prepare拒否','正常下書き保存','下書き読取・復元','旧下書きローカル復元','90日旧下書きサーバー読取・復元','他所有者下書きの拒否','30日CRF初回保存','30日CRF訂正v2','30日CRF履歴読取','90日CRF初回保存','90日CRF履歴読取','6月CRF初回保存','6月CRF履歴読取','古い版指定拒否','訂正理由なし拒否','直前の正常保存operationの状態確認','直前の正常保存operationの再実行']
    choice=st.selectbox('試験操作',choices)
    if st.button('選択した1操作を実行'):
        try:
            if choice=='接続・対象症例確認':r=context(st)
            elif choice=='識別入力prepare拒否':
                if st.session_state.get('auth04_privacy_next',0)==len(PRIVACY_FIXTURES):
                    st.info('全16条件の拒否確認済みです。再送しません。');st.stop()
                r=privacy_probe_once(st)
                st.write('拒否確認件数：'+str(st.session_state['auth04_privacy_next'])+'/'+str(len(PRIVACY_FIXTURES)))
            elif choice=='正常下書き保存':
                clear_session_state_prefixes(('peri_','widget_peri_'));restore_draft_state(draft_payload()['draft_state'])
                p=draft_payload();p['draft_state']=capture_draft_state('peri_');r=write_once(st,'save_draft',p)
                if r.get('ok') is not True or r.get('state')!='SAVED':raise PermissionError('NORMAL_DRAFT_SAVE_FAILED')
            elif choice=='下書き読取・復元':
                r=call(st,'get_draft',read_payload());result=r.get('result',{})
                if r.get('ok') is not True or result.get('source_found') is not True:raise PermissionError('DRAFT_READ_NOT_CONFIRMED')
                clear_session_state_prefixes(('peri_','widget_peri_'));restore_draft_state(result.get('draft_state') or {})
                restored=capture_draft_state('peri_')
                if restored!=draft_payload()['draft_state']:raise PermissionError('DRAFT_RESTORE_MISMATCH')
            elif choice=='旧下書きローカル復元':
                st.session_state['peri_patient_name']='完全架空旧値'
                legacy=copy.deepcopy(draft_payload()['draft_state']);legacy['peri_患者氏名']={'value':'完全架空旧値'}
                clear_session_state_prefixes(('peri_','widget_peri_'));restore_draft_state(legacy)
                if capture_draft_state('peri_')!=draft_payload()['draft_state'] or 'peri_patient_name' in st.session_state or 'peri_患者氏名' in st.session_state:raise PermissionError('LEGACY_RESTORE_FAILED')
                r={'ok':True};st.caption('画面内の旧形式復元のみ。サーバー旧下書きの所有権試験の代替にはしません。')
            elif choice=='90日旧下書きサーバー読取・復元':r=legacy90d_read_restore(st)
            elif choice=='他所有者下書きの拒否':r=other_owner_read_denied(st)
            elif choice=='30日CRF初回保存':r=save_expected_crf(st,0,1)
            elif choice=='30日CRF訂正v2':r=save_expected_crf(st,0,2)
            elif choice=='90日CRF初回保存':r=save_expected_crf(st,1,1)
            elif choice=='6月CRF初回保存':r=save_expected_crf(st,2,1)
            elif choice in ('30日CRF履歴読取','90日CRF履歴読取','6月CRF履歴読取'):
                r=verify_history(st,{'30日CRF履歴読取':0,'90日CRF履歴読取':1,'6月CRF履歴読取':2}[choice])
            elif choice in ('古い版指定拒否','訂正理由なし拒否'):
                p=crf_payload(0,2);p['submission_id']+='-NEGATIVE'
                if choice=='古い版指定拒否':p['expected_record_version']=0
                else:p['correction_reason']='';p['expected_record_version']=2
                r=write_once(st,'save_crf',p)
                expected_error='STALE_VERSION' if choice=='古い版指定拒否' else 'CORRECTION_REASON_REQUIRED'
                if r.get('ok') is not False or r.get('error')!=expected_error or r.get('state')!='FAILED':raise PermissionError('NEGATIVE_REASON_NOT_CONFIRMED')
            else:
                saved_id=st.session_state.get('auth04_last_saved_operation')
                if not saved_id:raise PermissionError('NO_OBSERVED_SAVED_OPERATION')
                action='request_status' if choice=='直前の正常保存operationの状態確認' else 'execute_request'
                r=call(st,action,{'operation_id':saved_id})
                if r.get('ok') is not True or r.get('state')!='SAVED':raise PermissionError('REPLAY_STATUS_NOT_CONFIRMED')
            st.session_state.setdefault('auth04_results',[]).append({'check':choice,**summarize(r)})
            render_progress(st)
        except PrepareWindowClosed:
            st.session_state['auth04_preparation_uncertain']=False
            st.warning('期限まで15分未満のため新しい保存要求を送信しません。読取・保存状態の照合後にログアウトしてください。')
        except Exception as exc:
            st.session_state['auth04_halted']=True
            st.session_state['auth04_last_exception_category']=safe_exception_category(exc)
            render_progress(st)
            st.error('実測を確認できないため停止しました。自動再送せず、監査と台帳を照合してください。')
    st.stop()

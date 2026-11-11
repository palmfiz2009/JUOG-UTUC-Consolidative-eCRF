"""Candidate bridge for saved Streamlit pages; isolated URL only, no fallback/retry."""
import json,hashlib,uuid,urllib.request
from urllib.parse import urlparse
from auth_bridge import signed_request
READS={'backend_info','ui_context','list_review_cases','get_screening_crf','get_own_review','list_screenings','get_screening','get_mdt_reviews','stats','get_screening_draft','get_draft','get_crf_linkage','validate','read_crf'}
DENIED='AKfycbxx9q3oD0RK_afxcivbu6LrtbwZZ_6ET6bVPEv-k9Gk7E0UNTL6S3ramekXU_IPQOeH'
def _post(st,action,operation,timeout):
    cfg=st.secrets['unified_test'];url=cfg['url'];u=urlparse(url)
    if cfg.get('enabled') is not True or cfg.get('release_approved') is not True or u.scheme!='https' or u.hostname!='script.google.com' or DENIED in url or url!=cfg['approved_url']:return {'ok':False,'error':'INTEGRATION_NOT_APPROVED'}
    envelope=signed_request(st,action,operation)
    req=urllib.request.Request(url,data=json.dumps(envelope,ensure_ascii=False).encode(),headers={'Content-Type':'application/json'},method='POST')
    with urllib.request.urlopen(req,timeout=timeout) as response:r=json.load(response)
    if not isinstance(r,dict):raise ValueError('INVALID_RESPONSE')
    return r

def registry_call(st,action,payload=None,timeout=30):
    try:
        p=json.loads(json.dumps(payload or {},default=str))
        if action=='save_crf':p=p.get('payload',p)
        if 'registration_id' in p:p['registration_id']=str(p['registration_id']).strip().upper()
        context={'id':'context','action':'ui_context','payload':{'registration_id':p.get('registration_id','')}}
        ctx=_post(st,'ui_context',context,timeout)
        if not ctx.get('ok'):return present_error(ctx)
        if action in {'backend_info','ui_context'}:return ctx
        if ctx['role']=='facility' and not p.get('facility_code'):
            site=ctx.get('facility_code')
            if not site:return {'ok':False,'error':'FACILITY_CONTEXT_REQUIRED'}
            p['facility_code']=site
        # Old UI names are display inputs; verified principal is the server actor.
        p.pop('admin_user',None);p.pop('reviewer_name',None)
        if action=='save_crf':
            pin=st.session_state.get('v3_base_pins',{}).get(p['record_key'])
            if not pin or pin['user_id']!=ctx['user_id']:return {'ok':False,'error':'BASE_VERSION_NOT_CONFIRMED'}
            p['expected_record_version']=pin['version'];p['schema_version']='review-v3-unapproved'
        if action in READS:
            op={'id':'read_'+uuid.uuid4().hex,'action':action,'payload':p,'expected_revision':ctx['revision']}
            reply=_post(st,action,op,timeout)
        else:
            prepared=_post(st,'prepare_request',{'action':action,'payload':p},timeout)
            if not prepared.get('ok'):return present_error(prepared)
            # Only the operation ID is cached. Full request lives in the authorized server journal.
            st.session_state['v3_last_operation_id']=prepared['operation_id']
            reply=_post(st,'execute_request',{'operation_id':prepared['operation_id']},timeout)
        if not reply.get('ok'):return present_error(reply)
        if action not in READS and reply.get('state')!='SAVED':return present_error({'ok':False,'state':'UNKNOWN','error':'AUDIT_NOT_CONFIRMED'})
        result=dict(reply.get('result',{}));result['ok']=True
        if 'resume_code' in reply:result['resume_code']=reply['resume_code']
        result['_domain_revision']=reply.get('revision')
        return result
    except PermissionError:return present_error({'ok':False,'error':'OIDC_REAUTHENTICATION_REQUIRED'})
    except Exception:return present_error({'ok':False,'state':'UNKNOWN','error':'REQUEST_UNCERTAIN_RECONCILE_BEFORE_RETRY'})

def role_gate(st,allowed):
    if not st.user.is_logged_in:
        if st.button('個人アカウントでログイン'):st.login()
        return None
    ctx=registry_call(st,'ui_context')
    if not ctx.get('ok') or ctx.get('role') not in allowed:
        st.error('この画面の個人権限を確認できません。')
        if st.button('ログアウトして本人認証をやり直す'):st.logout()
        return None
    render_recovery_controls(st)
    return ctx['role']

def render_base_version_control(st,registration_id,crf_type,visit):
    if not registration_id:return
    key='|'.join([registration_id.strip().upper(),crf_type,visit])
    if st.button('確定済み履歴を読み込み、訂正の基準版を確認',key='base_'+key):
        ctx=registry_call(st,'ui_context',{'registration_id':registration_id})
        result=registry_call(st,'read_crf',{'registration_id':registration_id,'record_key':key})
        if not ctx.get('ok') or not result.get('ok'):st.error('確定版を確認できません。保存は停止しています。');return
        records=result.get('records',[]);version=max([r['record_version'] for r in records],default=0)
        st.session_state.setdefault('v3_base_pins',{})[key]={'version':version,'user_id':ctx['user_id']}
        st.session_state.setdefault('v3_base_history',{})[key]=records
    pin=st.session_state.get('v3_base_pins',{}).get(key)
    if pin:
        st.caption('保存時に照合する基準版：'+str(pin['version']))
        with st.expander('読み込んだ確定済み履歴'):st.json(st.session_state.get('v3_base_history',{}).get(key,[]))
    else:st.info('正式保存の前に、上のボタンで確定済み履歴を確認してください。')


def present_error(result):
    r=dict(result);code=r.get('error','');state=r.get('state')
    if code in {'OIDC_REAUTHENTICATION_REQUIRED','AUTH_REQUIRED','AUTH_EXPIRED','AUTH_INVALID'}:message='認証の有効期限または本人確認を確認できません。再ログインしてください。'
    elif code in {'STALE_VERSION','STALE_DOMAIN_REVISION'}:message='基準版または台帳状態が更新されています。確定履歴を確認し、訂正内容を見直してください。'
    elif code in {'ROLE_NOT_ALLOWED','FACILITY_FORBIDDEN','SUBJECT_FORBIDDEN','REQUEST_NOT_AUTHORIZED'}:message='この操作の権限がありません。'
    elif state=='UNKNOWN' or code in {'REQUEST_UNCERTAIN_RECONCILE_BEFORE_RETRY','PREPARATION_UNCERTAIN','STATUS_UNVERIFIABLE'}:message='保存状態を確認できません。新しい申請を送らず「保存状態確認・安全な再開」で照合してください。'
    elif state=='UNFINISHED' or code in {'UNFINISHED_REQUEST_BLOCKS_NEW_OPERATION','UNKNOWN_REQUEST_BLOCKS_NEW_OPERATION','DOMAIN_RECOVERY_REQUIRED'}:message='未確定の要求があります。監査完了前のため保存成功とは扱いません。保存状態を確認してください。'
    elif state=='FAILED':message='要求は保存前に拒否されました。表示された条件を修正してください。'
    else:message='保存を完了できませんでした。条件と保存状態を確認してください。'
    r['message']=message;return r

def recovery_call(st,action,operation_id=None):
    try:return _post(st,action,{'operation_id':operation_id} if operation_id else {},30)
    except PermissionError:return present_error({'ok':False,'error':'OIDC_REAUTHENTICATION_REQUIRED'})
    except Exception:return present_error({'ok':False,'state':'UNKNOWN','error':'STATUS_UNVERIFIABLE'})

def render_recovery_controls(st):
    # No localStorage, cookies containing clinical payload, file cache or URL parameters.
    with st.expander('保存状態確認・安全な再開'):
        listing=recovery_call(st,'list_requests')
        if not listing.get('ok'):
            st.error(present_error(listing)['message']);return
        rows=listing.get('requests',[])
        if not rows:st.caption('この個人IDで確認できる保存要求はありません。');return
        active=[r for r in rows if r['state'] not in {'SAVED','FAILED'}]
        items=active+[r for r in rows if r not in active][-10:]
        labels={'SAVED':'保存済み（監査確定）','UNFINISHED':'未完了','FAILED':'失敗（保存前拒否）','UNKNOWN':'確認不能'}
        selected=st.selectbox('照合する要求',items,format_func=lambda r:labels[r['state']]+' / '+r['action']+' / '+r['operation_id'],key='v3_recovery_selection')
        if st.button('保存状態を照合',key='v3_check_status'):
            result=recovery_call(st,'request_status',selected['operation_id'])
            if result.get('ok'):st.info(labels.get(result.get('state'),'確認不能')+' / '+result.get('phase',''))
            else:st.error(present_error(result)['message'])
        if selected['state']=='UNFINISHED':
            confirm=st.checkbox('保存された元の要求を、同じ操作IDで再開する',key='v3_confirm_resume_'+selected['operation_id'])
            if st.button('同じ操作IDで安全に再開',disabled=not confirm,key='v3_resume'):
                result=recovery_call(st,'execute_request',selected['operation_id'])
                if result.get('ok') and result.get('state')=='SAVED':st.success('保存と監査の確定を確認しました。確定履歴を再読込してください。')
                else:st.error(present_error(result)['message'])
        elif selected['state']=='UNKNOWN':st.warning('自動再送できません。管理者による監査・保存状態の照合が必要です。')

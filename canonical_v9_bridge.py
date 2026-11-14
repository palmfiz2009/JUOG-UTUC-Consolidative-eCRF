"""Canonical form -> V9 request contract. No network implementation, tokens or fallback.
Production entry may ONLY call preview. Request signing never implies ACL acceptance.
"""
import copy,hashlib,json,uuid
from uat_b2_auth_bridge import signed_request
CASE='JUOG-971';FACILITY='TEST01';PAIR=('perioperative_30d','30d')
class BridgeError(PermissionError):pass

def canonical(value):return json.dumps(value,ensure_ascii=False,separators=(',',':'),sort_keys=True,allow_nan=False)

def authorize_context(response):
    if not (response.get('ok') is True and response.get('role')=='facility' and response.get('facilities')==[FACILITY] and response.get('facility_code')==FACILITY and response.get('execution_stage')=='AUTH_CONNECT' and response.get('business_writes_allowed') is False):raise BridgeError('ACL_NOT_CONFIRMED')

def operation(action,payload,redact,versions):
    p=copy.deepcopy(payload.get('payload',{}) if action=='save_crf' else payload)
    if action not in ('save_crf','save_draft','get_draft','read_crf'):raise BridgeError('ACTION_NOT_ALLOWED')
    if p.get('registration_id')!=CASE:raise BridgeError('CASE_NOT_ALLOWED')
    if p.get('facility_code',FACILITY)!=FACILITY:raise BridgeError('FACILITY_NOT_ALLOWED')
    if any(k in p for k in ('actor','user_id','subject','issuer','role','actor_auth','token')):raise BridgeError('ACTOR_OVERRIDE_FORBIDDEN')
    p['facility_code']=FACILITY
    if action in ('save_crf','save_draft'):
        if p.get('schema_version') not in (None,'2026-09-14-v2.2.2','review-v3-unapproved'):
            raise BridgeError('SCHEMA_VERSION_NOT_SUPPORTED')
        p['schema_version']='review-v3-unapproved'
    if action=='save_crf' and p.get('study_code')!='JUOG_UTUC_Consolidative':
        raise BridgeError('STUDY_CODE_INVALID')
    if action=='read_crf':
        if p.get('record_key')!='|'.join((CASE,*PAIR)):raise BridgeError('RECORD_NOT_ALLOWED')
        p={k:p[k] for k in ('registration_id','facility_code','record_key')}
    else:
        if (p.get('crf_type'),p.get('visit'))!=PAIR:raise BridgeError('CRF_NOT_ALLOWED')
        if p.get('reporter_email')!='fictional@example.invalid':raise BridgeError('FICTIONAL_CONTACT_REQUIRED')
        if canonical(redact(p))!=canonical(p):raise BridgeError('DIRECT_IDENTIFIER_REJECTED')
        key='|'.join((CASE,*PAIR))
        if action=='save_crf':
            if p.get('record_key') not in (None,key):raise BridgeError('RECORD_NOT_ALLOWED')
            p['record_key']=key
            kind=p.get('submission_kind')
            if kind=='初回報告':p['expected_record_version']=0
            elif kind=='訂正報告':
                if not str(p.get('correction_reason','')).strip():raise BridgeError('CORRECTION_REASON_REQUIRED')
                version=versions.get(key)
                if type(version) is not int or version<1:raise BridgeError('VERIFIED_RECORD_VERSION_REQUIRED')
                p['expected_record_version']=version
            else:raise BridgeError('SUBMISSION_KIND_INVALID')
    return {'action':action,'payload':p}

def build(native,action,payload,redact,versions,state):
    op=operation(action,payload,redact,versions)
    if action in ('save_crf','save_draft'):
        # Keep the same submission identity for the same content. Do not create a server operation ID.
        clean=copy.deepcopy(op);clean['payload'].pop('submission_id',None);clean['payload'].pop('submitted_at',None)
        digest=hashlib.sha256(canonical(clean).encode()).hexdigest()
        slot=state.setdefault('canonical_v9_previews',{})
        if digest not in slot:slot[digest]={'submission_id':uuid.uuid4().hex,'submitted_at':op['payload'].get('submitted_at')}
        if action=='save_crf':op['payload'].update(slot[digest])
        envelope=signed_request(native,'prepare_request',op)
    else:
        envelope=signed_request(native,action,{'id':'canonical_read_'+uuid.uuid4().hex,**op})
    return envelope,op

def preview(native,context_response,action,payload,redact,versions,state):
    authorize_context(context_response)
    envelope,op=build(native,action,payload,redact,versions,state)
    # Never return the envelope, raw response, principal, token or clinical data to the UI.
    del envelope
    return {'ok':False,'error':'PREVIEW_ONLY_NOT_SENT','preview_valid':True,'action':op['action'],
            'subject_registry_verified':False,'server_operation_created':False,'business_sent':False}

def safe_read_result(result,redact):
    if result.get('ok') is not True:return {'ok':False,'error':'READ_NOT_CONFIRMED'}
    out=redact(copy.deepcopy(result))
    return out

class Lifecycle:
    """Transport-injected contract runner for offline tests ONLY; runtime preview never uses it.
    Once prepare is attempted, uncertainty blocks new operations until explicit status reconciliation.
    """
    def __init__(self,call):self.call=call;self.pending=None;self.uncertain=False
    def write(self,op):
        if self.pending or self.uncertain:raise BridgeError('RECONCILE_BEFORE_NEW_PREPARE')
        self.uncertain=True
        prepared=self.call('prepare_request',op)
        if prepared.get('state')=='UNKNOWN' or prepared.get('error') in ('PREPARATION_UNCERTAIN','REQUEST_UNCERTAIN_RECONCILE_BEFORE_RETRY'):raise BridgeError('PREPARATION_UNCERTAIN')
        if prepared.get('ok') is not True:self.uncertain=False;return prepared
        opid=prepared.get('operation_id')
        if not isinstance(opid,str) or not opid:raise BridgeError('INVALID_OPERATION_ID')
        self.pending=opid;self.uncertain=False
        self.call('execute_request',{'operation_id':opid})
        return self.reconcile()
    def reconcile(self):
        if not self.pending:raise BridgeError('NO_OBSERVED_OPERATION')
        result=self.call('request_status',{'operation_id':self.pending})
        if result.get('ok') is True and result.get('state')=='SAVED':self.pending=None
        return result

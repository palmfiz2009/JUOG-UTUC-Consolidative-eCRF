"""Undeployed signed read-only probe. No business writes, no raw clinical output."""
import time, hashlib, re
from uat_b2_auth_bridge import signed_request
SCOPE={'registration_id':'JUOG-971','facility_code':'TEST01','record_key':'JUOG-971|perioperative_30d|30d'}
SHA='5b7c086bee4afe98efc8c140204110765f9f8b534422e4ebe273bd85c2a89fbe'
ACL_END=1795100340  # 2026-11-19 23:59 JST

def gate(cfg,now):
    if not (cfg.get('approved') is True and cfg.get('candidate_sha256')==SHA
        and cfg.get('scope')==SCOPE and cfg.get('write_approved') is False
        and isinstance(cfg.get('review_ref'),str) and cfg['review_ref'].strip()
        and type(cfg.get('starts_at')) is int and type(cfg.get('expires_at')) is int
        and cfg['starts_at']<=now<cfg['expires_at']<=min(cfg['starts_at']+1800,ACL_END)):
        raise PermissionError('READ_PROBE_NOT_APPROVED')

def probe(native_provider,transport,cfg,clock=time.time):
    def call(action,payload):
        gate(cfg,int(clock()))
        if action not in ('list_requests','read_crf','request_status'):raise PermissionError('READ_SCOPE')
        result=transport(signed_request(native_provider(),action,payload))
        gate(cfg,int(clock()))
        if not isinstance(result,dict) or result.get('ok') is not True:raise PermissionError('READ_NOT_CONFIRMED')
        return result
    listing=call('list_requests',dict(SCOPE))
    if listing.get('read_only') is not True or listing.get('record_key')!=SCOPE['record_key']:raise PermissionError('SCOPE_NOT_CONFIRMED')
    rows=listing.get('requests')
    if not isinstance(rows,list) or len(rows)>100:raise PermissionError('REQUESTS_UNVERIFIABLE')
    seen=set(); submissions=set(); summaries=[]
    for row in rows:
        if not isinstance(row,dict):raise PermissionError('REQUESTS_UNVERIFIABLE')
        oid=row.get('operation_id');sid=row.get('submission_id')
        if not isinstance(oid,str) or not re.fullmatch('[A-Za-z0-9_-]{1,128}',oid) or oid in seen or not isinstance(sid,str) or not re.fullmatch('[A-Za-z0-9_-]{1,128}',sid) or sid in submissions:raise PermissionError('REQUESTS_UNVERIFIABLE')
        if type(row.get('expected_record_version')) is not int or row['expected_record_version']<0:raise PermissionError('REQUEST_METADATA_INVALID')
        phases={'SAVED':('COMMITTED',),'FAILED':('REJECTED_BEFORE_INTENT',),'UNFINISHED':('PREPARED','AUDIT_OR_COMMIT_PENDING')}
        if row.get('phase') not in phases.get(row.get('state'),()) or not isinstance(row.get('content_sha256'),str) or not re.fullmatch('[a-f0-9]{64}',row['content_sha256']):raise PermissionError('REQUEST_METADATA_INVALID')
        seen.add(oid);submissions.add(sid)
        status=call('request_status',{'operation_id':oid})
        if status.get('action')!='save_crf' or status.get('operation_id')!=oid or status.get('state')!=row.get('state') or status.get('phase')!=row.get('phase'):raise PermissionError('STATUS_MISMATCH')
        summaries.append({'operation_sha256':hashlib.sha256(oid.encode()).hexdigest(),'submission_sha256':hashlib.sha256(sid.encode()).hexdigest(),'state':row['state'],'phase':row['phase'],'content_sha256':row.get('content_sha256')})
    read=call('read_crf',{'id':'readonly-971-30d','action':'read_crf','payload':dict(SCOPE)})
    if read.get('read_only') is not True:raise PermissionError('READ_NOT_CONFIRMED')
    result=read.get('result')
    if not isinstance(result,dict) or result.get('ok') is not True:raise PermissionError('NESTED_READ_FAILED')
    records=result.get('records')
    if not isinstance(records,list) or not records:raise PermissionError('RECORD_NOT_CONFIRMED')
    for r in records:
        if not isinstance(r,dict):raise PermissionError('RECORD_SCOPE')
        p=r.get('payload')
        if r.get('record_key')!=SCOPE['record_key'] or not isinstance(r.get('submission_id'),str) or not r['submission_id'] or not isinstance(p,dict) or any(p.get(k)!=v for k,v in {'registration_id':'JUOG-971','facility_code':'TEST01','crf_type':'perioperative_30d','visit':'30d'}.items()):raise PermissionError('RECORD_SCOPE')
    versions=[r.get('record_version') for r in records]
    if any(type(v) is not int or v<1 for v in versions) or sorted(versions)!=list(range(1,max(versions)+1)):raise PermissionError('VERSION_GAP')
    record_submissions=[r['submission_id'] for r in records]
    if len(set(record_submissions))!=len(record_submissions):raise PermissionError('DUPLICATE_SUBMISSION')
    by_submission={r['submission_id']:r for r in records}
    for row in rows:
        record=by_submission.get(row['submission_id'])
        if row['state']=='SAVED':
            if record is None or record['record_version']!=row['expected_record_version']+1:raise PermissionError('COMMITTED_RECORD_MISMATCH')
        elif record is not None:
            raise PermissionError('REQUEST_RECORD_STATE_MISMATCH')
    # Return only metadata; human reconciliation of legacy submissions is explicit.
    return {'read_only':True,'scope':dict(SCOPE),'versions':sorted(versions),'latest_version':max(versions),'v3_correction_candidate':max(versions)==2,'requests':summaries,'business_writes':0,'manual_submission_content_audit_reconciliation_required':True}

"""Read-only discovery after local state loss. Never prepare/execute implicitly."""
import re
from canonical_v9_bridge import BridgeError,CASE,FACILITY,PAIR
KEY='|'.join((CASE,*PAIR))
PHASES={'UNFINISHED':{'PREPARED','AUDIT_OR_COMMIT_PENDING'},'SAVED':{'COMMITTED'},'FAILED':{'REJECTED_BEFORE_INTENT'}}
FIELDS={'operation_id','submission_id','state','phase','expected_record_version','content_sha256'}
def valid_id(value):return isinstance(value,str) and re.fullmatch(r'[A-Za-z0-9_-]{1,128}',value) is not None

def discover(call):
 r=call('list_requests',{'registration_id':CASE,'facility_code':FACILITY,'record_key':KEY})
 if not isinstance(r,dict) or r.get('ok') is not True or r.get('read_only') is not True or r.get('record_key')!=KEY or not isinstance(r.get('requests'),list):raise BridgeError('RECOVERY_READ_NOT_CONFIRMED')
 rows=r['requests'];seen=set()
 for row in rows:
  if not isinstance(row,dict) or set(row)-FIELDS or not valid_id(row.get('operation_id')) or row['operation_id'] in seen:raise BridgeError('RECOVERY_ROW_INVALID')
  if not isinstance(row.get('state'),str) or not isinstance(row.get('phase'),str) or row['phase'] not in PHASES.get(row['state'],set()):raise BridgeError('RECOVERY_ROW_INVALID')
  if 'submission_id' in row and not valid_id(row['submission_id']):raise BridgeError('RECOVERY_ROW_INVALID')
  if 'expected_record_version' in row and (type(row['expected_record_version']) is not int or row['expected_record_version']<0):raise BridgeError('RECOVERY_ROW_INVALID')
  if 'content_sha256' in row and (not isinstance(row['content_sha256'],str) or not re.fullmatch('[a-f0-9]{64}',row['content_sha256'])):raise BridgeError('RECOVERY_ROW_INVALID')
  seen.add(row['operation_id'])
 pending=[v for v in rows if v['state']=='UNFINISHED']
 if len(pending)>1:raise BridgeError('AMBIGUOUS_RECOVERY')
 if not pending:return {'state':'NO_PENDING_OBSERVED','may_prepare':False,'may_execute':False,'requests':rows}
 q=pending[0];opid=q.get('operation_id')
 if not isinstance(opid,str) or not opid:raise BridgeError('RECOVERY_ID_INVALID')
 status=call('request_status',{'operation_id':opid})
 if not isinstance(status,dict) or status.get('ok') is not True or status.get('operation_id')!=opid or status.get('action')!='save_crf' or not isinstance(status.get('state'),str) or not isinstance(status.get('phase'),str) or status['phase'] not in PHASES.get(status['state'],set()):raise BridgeError('RECOVERY_STATUS_UNCONFIRMED')
 return {'state':status['state'],'operation_id':opid,'may_prepare':False,'may_execute':False,'requires_content_reconciliation':True}

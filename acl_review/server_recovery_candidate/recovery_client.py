"""Read-only discovery after local state loss. Never prepare/execute implicitly."""
from canonical_v9_bridge import BridgeError,CASE,FACILITY,PAIR
KEY='|'.join((CASE,*PAIR))
def discover(call):
 r=call('list_requests',{'registration_id':CASE,'facility_code':FACILITY,'record_key':KEY})
 if r.get('ok') is not True or r.get('read_only') is not True or r.get('record_key')!=KEY or not isinstance(r.get('requests'),list):raise BridgeError('RECOVERY_READ_NOT_CONFIRMED')
 rows=r['requests'];pending=[v for v in rows if v.get('state')=='UNFINISHED']
 if len(pending)>1:raise BridgeError('AMBIGUOUS_RECOVERY')
 if not pending:return {'state':'NO_PENDING_OBSERVED','may_prepare':False,'requests':rows}
 q=pending[0];opid=q.get('operation_id')
 if not isinstance(opid,str) or not opid:raise BridgeError('RECOVERY_ID_INVALID')
 status=call('request_status',{'operation_id':opid})
 if status.get('ok') is not True or status.get('operation_id')!=opid or status.get('action')!='save_crf' or status.get('state') not in ('UNFINISHED','SAVED','FAILED'):raise BridgeError('RECOVERY_STATUS_UNCONFIRMED')
 return {'state':status['state'],'operation_id':opid,'may_prepare':False,'may_execute':False,'requires_content_reconciliation':True}

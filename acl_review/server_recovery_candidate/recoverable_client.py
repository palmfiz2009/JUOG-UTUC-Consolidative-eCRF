"""Offline candidate: recover a lost prepare response, never execute implicitly.
Requires retained local attempt plus independently re-supplied identical content.
Total loss of the local store still requires manual reconciliation; not a live store.
"""
import copy,hashlib,re,struct,math,json
from client import Client,KEY,semantic_json
from canonical_v9_bridge import BridgeError,operation,CASE,FACILITY
def recovery_fingerprint(value):
 def typed(v):
  if v is None:return ['null']
  if isinstance(v,bool):return ['boolean',v]
  if isinstance(v,str):return ['string',v]
  if isinstance(v,(int,float)):
   if not math.isfinite(v):raise BridgeError('RECOVERY_NUMBER_INVALID')
   return ['number',struct.pack('>d',0.0 if v==0 else float(v)).hex()]
  if isinstance(v,list):return ['array',[typed(x) for x in v]]
  if isinstance(v,dict):return ['object',[[k,typed(v[k])] for k in sorted(v,key=lambda x:x.encode('utf-16-be','surrogatepass'))]]
  raise BridgeError('RECOVERY_VALUE_INVALID')
 return hashlib.sha256(json.dumps(typed(value),ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()).hexdigest()
class RecoverableClient(Client):
 def recover_prepare(self,digest,payload):
  if self._identity_hash()!=self.actor:raise BridgeError('PRINCIPAL_CHANGED')
  row=self._row(digest)
  if not row or row[1]!=self.actor or row[2]!='PREPARING' or row[3]:raise BridgeError('RECOVERY_ATTEMPT_INVALID')
  op=operation('save_crf',{'payload':copy.deepcopy(payload)},self.redact,{KEY:row[5]})
  op['payload'].pop('submission_id',None);op['payload'].pop('submitted_at',None)
  canonical=semantic_json(op)
  if hashlib.sha256((self.actor+'|'+canonical).encode()).hexdigest()!=digest:raise BridgeError('RECOVERY_CONTENT_MISMATCH')
  r=self.call('list_requests',{'registration_id':CASE,'facility_code':FACILITY,'record_key':KEY})
  if r.get('ok') is not True or r.get('read_only') is not True or r.get('record_key')!=KEY or not isinstance(r.get('requests'),list):raise BridgeError('RECOVERY_READ_NOT_CONFIRMED')
  rows=r['requests']
  if any(not isinstance(x,dict) for x in rows):raise BridgeError('RECOVERY_READ_NOT_CONFIRMED')
  found=[x for x in rows if x.get('submission_id')==row[4]]
  if len(found)!=1:raise BridgeError('RECOVERY_NOT_UNIQUE')
  q=found[0];oid=q.get('operation_id')
  if not isinstance(oid,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}',oid) or type(q.get('expected_record_version')) is not int or q['expected_record_version']!=row[5] or q.get('content_sha256')!=recovery_fingerprint(op):raise BridgeError('RECOVERY_CONTENT_MISMATCH')
  # Authenticate status before recording a recovered server identity. No execute.
  status=self.call('request_status',{'operation_id':oid})
  phases={'UNFINISHED':{'PREPARED','AUDIT_OR_COMMIT_PENDING'},'SAVED':{'COMMITTED'},'FAILED':{'REJECTED_BEFORE_INTENT'}}
  if status.get('ok') is not True or status.get('operation_id')!=oid or status.get('action')!='save_crf' or status.get('phase') not in phases.get(status.get('state'),set()):raise BridgeError('RECOVERY_STATUS_UNCONFIRMED')
  self._set(digest,'PREPARED',oid)
  return self.reconcile(digest)

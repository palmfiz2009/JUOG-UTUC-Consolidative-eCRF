"""Offline candidate: recover a lost prepare response, never execute implicitly.
Requires retained local attempt plus independently re-supplied identical content.
Total loss of the local store still requires manual reconciliation; not a live store.
"""
import copy,hashlib,re
from client import Client,KEY,semantic_json
from recovery_client import validated_rows
from canonical_v9_bridge import BridgeError,operation,CASE,FACILITY
from content_fingerprint import recovery_fingerprint
class RecoverableClient(Client):
 def write(self,payload):
  # A new/empty local store is not proof that no earlier request exists.
  r=self.call('list_requests',{'registration_id':CASE,'facility_code':FACILITY,'record_key':KEY})
  rows=validated_rows(r)
  known={row[0]:row for row in self.db.execute('SELECT submission_id,operation_id,base,state FROM attempts WHERE actor=?',(self.actor,))}
  seen=set()
  for request in rows:
   sid=request.get('submission_id')
   if sid not in known:raise BridgeError('LOCAL_STATE_LOST_MANUAL_RECONCILIATION')
   local=known[sid]
   if sid in seen or (local[1] is not None and request['operation_id']!=local[1]) or type(request.get('expected_record_version')) is not int or request['expected_record_version']!=local[2]:raise BridgeError('RECOVERY_JOURNAL_BINDING_MISMATCH')
   if local[3] in ('SAVED','FAILED') and request['state']!=local[3]:raise BridgeError('RECOVERY_JOURNAL_BINDING_MISMATCH')
   seen.add(sid)
  # The scoped server contract returns the complete journal (or rejects it),
  # never a page. Missing a previously bound request is an unresolved mismatch.
  if any(local[1] is not None and sid not in seen for sid,local in known.items()):raise BridgeError('RECOVERY_JOURNAL_INCOMPLETE')
  return super().write(payload)
 def recover_prepare(self,digest,payload):
  if self._identity_hash()!=self.actor:raise BridgeError('PRINCIPAL_CHANGED')
  row=self._row(digest)
  if not row or row[1]!=self.actor or row[2]!='PREPARING' or row[3]:raise BridgeError('RECOVERY_ATTEMPT_INVALID')
  op=operation('save_crf',{'payload':copy.deepcopy(payload)},self.redact,{KEY:row[5]})
  op['payload'].pop('submission_id',None);op['payload'].pop('submitted_at',None)
  canonical=semantic_json(op)
  if hashlib.sha256((self.actor+'|'+canonical).encode()).hexdigest()!=digest:raise BridgeError('RECOVERY_CONTENT_MISMATCH')
  r=self.call('list_requests',{'registration_id':CASE,'facility_code':FACILITY,'record_key':KEY})
  rows=validated_rows(r)
  found=[x for x in rows if x.get('submission_id')==row[4]]
  if len(found)!=1:raise BridgeError('RECOVERY_NOT_UNIQUE')
  q=found[0];oid=q.get('operation_id')
  if not isinstance(oid,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}',oid) or type(q.get('expected_record_version')) is not int or q['expected_record_version']!=row[5] or q.get('content_sha256')!=recovery_fingerprint(op):raise BridgeError('RECOVERY_CONTENT_MISMATCH')
  # Authenticate status before recording a recovered server identity. No execute.
  status=self.call('request_status',{'operation_id':oid})
  phases={'UNFINISHED':{'PREPARED','AUDIT_OR_COMMIT_PENDING'},'SAVED':{'COMMITTED'},'FAILED':{'REJECTED_BEFORE_INTENT'}}
  if status.get('ok') is not True or status.get('operation_id')!=oid or status.get('action')!='save_crf' or status.get('phase') not in phases.get(status.get('state'),set()):raise BridgeError('RECOVERY_STATUS_UNCONFIRMED')
  # A newer status may advance, but cannot contradict a terminal listing or
  # turn an already-started execution back into a safely executable request.
  if (q['state'] in ('SAVED','FAILED') and status['state']!=q['state']) or (q['phase']=='AUDIT_OR_COMMIT_PENDING' and status['phase']=='PREPARED'):raise BridgeError('RECOVERY_STATUS_REGRESSION')
  with self.db:
   claimed=self.db.execute("UPDATE attempts SET state='PREPARED',operation_id=? WHERE digest=? AND actor=? AND state='PREPARING' AND operation_id IS NULL",(oid,digest,self.actor)).rowcount
  if claimed!=1:
   current=self._row(digest)
   if not current or current[1]!=self.actor or current[3]!=oid:raise BridgeError('RECOVERY_BIND_CONFLICT')
  # A concurrent EXECUTING/SAVED row must never be rewound to PREPARED.
  return self.reconcile(digest)

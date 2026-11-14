"""OFFLINE integration candidate. No HTTP transport or runtime activation.
SQLite is a local regression store, NOT an approved Streamlit persistent store.
The caller's transport must enforce native OIDC/ACL/signature/session on EVERY call.
"""
import copy,hashlib,json,sqlite3,uuid
from canonical_v9_bridge import operation,canonical,BridgeError,CASE,FACILITY,PAIR
KEY='|'.join((CASE,*PAIR))
def semantic_json(value):
 def normalize(v):
  if isinstance(v,dict):return {k:normalize(x) for k,x in v.items()}
  if isinstance(v,list):return [normalize(x) for x in v]
  if isinstance(v,float) and v.is_integer():return int(v)
  return v
 return canonical(normalize(value))
class Client:
 def __init__(self,call,redact,path,identity):
  self.transport,self.redact,self.identity=call,redact,identity
  self.actor=self._identity_hash()
  self.db=sqlite3.connect(path,timeout=5)
  self.db.execute('CREATE TABLE IF NOT EXISTS attempts (digest TEXT PRIMARY KEY, actor TEXT NOT NULL, state TEXT NOT NULL, operation_id TEXT, submission_id TEXT NOT NULL, base INTEGER NOT NULL)')
  self.db.commit();self.observed=None
 def _identity_hash(self):
  identity=self.identity()
  if not isinstance(identity,dict) or set(identity)!= {'issuer','subject','environment'} or identity.get('environment')!='JUOG_AUTH04_ISOLATED_TEST01' or any(not isinstance(v,str) or not v for v in identity.values()):raise BridgeError('VERIFIED_IDENTITY_REQUIRED')
  return hashlib.sha256(canonical(identity).encode()).hexdigest()
 def call(self,action,payload):
  if self._identity_hash()!=self.actor:raise BridgeError('PRINCIPAL_CHANGED')
  return self.transport(action,payload)
 def close(self):self.db.close()
 def read(self):
  self.observed=None
  r=self.call('read_crf',{'id':'read_'+uuid.uuid4().hex,'action':'read_crf','payload':{'registration_id':CASE,'facility_code':FACILITY,'record_key':KEY}})
  if r.get('ok') is not True or r.get('read_only') is not True or r.get('result',{}).get('ok') is not True:raise BridgeError('READ_NOT_CONFIRMED')
  records=r['result'].get('records')
  if not isinstance(records,list):raise BridgeError('READ_SHAPE_INVALID')
  records=sorted(copy.deepcopy(records),key=lambda v:v.get('record_version',-1))
  for n,rec in enumerate(records,1):
   p=rec.get('payload',{})
   if type(rec.get('record_version')) is not int or rec['record_version']!=n or rec.get('record_key')!=KEY or p.get('registration_id')!=CASE or p.get('facility_code')!=FACILITY or (p.get('crf_type'),p.get('visit'))!=PAIR:raise BridgeError('READ_SCOPE_OR_VERSION_INVALID')
  self.observed=len(records)
  return {'ok':True,'record_version':self.observed,'records':self.redact(records)}
 def _row(self,digest):return self.db.execute('SELECT digest,actor,state,operation_id,submission_id,base FROM attempts WHERE digest=?',(digest,)).fetchone()
 def _set(self,digest,state,opid=None):
  self.db.execute('UPDATE attempts SET state=?,operation_id=COALESCE(?,operation_id) WHERE digest=?',(state,opid,digest));self.db.commit()
 def write(self,payload):
  if self._identity_hash()!=self.actor:raise BridgeError('PRINCIPAL_CHANGED')
  if self.observed is None:raise BridgeError('AUTHENTICATED_READ_REQUIRED')
  p=copy.deepcopy(payload)
  if p.get('submission_kind')=='初回報告' and self.observed!=0:raise BridgeError('INITIAL_ALREADY_EXISTS')
  op=operation('save_crf',{'payload':p},self.redact,{KEY:self.observed})
  semantic=copy.deepcopy(op);semantic['payload'].pop('submission_id',None);semantic['payload'].pop('submitted_at',None)
  digest=hashlib.sha256((self.actor+'|'+semantic_json(semantic)).encode()).hexdigest()
  try:
   self.db.execute('BEGIN IMMEDIATE')
   row=self._row(digest)
   if row:
    self.db.commit()
    if row[1]!=self.actor:raise BridgeError('OWNER_MISMATCH')
    return self.reconcile(digest)
   if self.db.execute("SELECT 1 FROM attempts WHERE state NOT IN ('SAVED','FAILED') LIMIT 1").fetchone():raise BridgeError('UNRESOLVED_ATTEMPT_BLOCKS_WRITE')
   sid=uuid.uuid4().hex
   self.db.execute('INSERT INTO attempts VALUES (?,?,?,?,?,?)',(digest,self.actor,'PREPARING',None,sid,self.observed));self.db.commit()
  except Exception:
   self.db.rollback();raise
  op['payload']['submission_id']=sid
  # PREPARING is durably recorded BEFORE crossing the transport boundary.
  prepared=self.call('prepare_request',op)
  if prepared.get('ok') is not True:
   # No blanket retry: even negative responses may represent an uncertain append.
   raise BridgeError('PREPARE_NOT_CONFIRMED')
  opid=prepared.get('operation_id')
  if not isinstance(opid,str) or not opid or len(opid)>128:raise BridgeError('OPERATION_ID_INVALID')
  self._set(digest,'PREPARED',opid)
  return self.resume(digest)
 def reconcile(self,digest):
  row=self._row(digest)
  if not row or row[1]!=self.actor:raise BridgeError('ATTEMPT_NOT_OWNED')
  if not row[3]:raise BridgeError('PREPARE_RESPONSE_LOST_MANUAL_RECONCILIATION')
  r=self.call('request_status',{'operation_id':row[3]})
  if r.get('ok') is not True or r.get('operation_id')!=row[3] or r.get('action')!='save_crf':raise BridgeError('STATUS_NOT_CONFIRMED')
  if r.get('state')=='SAVED' and r.get('phase')=='COMMITTED':
   saved=self.read();matches=[x for x in saved['records'] if x.get('submission_id')==row[4]]
   if len(matches)!=1 or matches[0]['record_version']!=row[5]+1:raise BridgeError('SAVE_READBACK_MISMATCH')
   confirmed=copy.deepcopy(matches[0]['payload']);confirmed.pop('submission_id',None);confirmed.pop('submitted_at',None)
   if hashlib.sha256((self.actor+'|'+semantic_json({'action':'save_crf','payload':confirmed})).encode()).hexdigest()!=digest:raise BridgeError('SAVE_CONTENT_MISMATCH')
   self._set(digest,'SAVED');self.observed=None
   return {'ok':True,'state':'SAVED','operation_id':row[3],'record_version':matches[0]['record_version']}
  if r.get('state')=='FAILED' and r.get('phase')=='REJECTED_BEFORE_INTENT':self._set(digest,'FAILED')
  return {'ok':False,'state':r.get('state','UNKNOWN'),'operation_id':row[3]}
 def resume(self,digest):
  row=self._row(digest)
  if not row or row[1]!=self.actor or not row[3]:raise BridgeError('ATTEMPT_NOT_OWNED')
  status=self.reconcile(digest)
  if status['state']!='UNFINISHED':return status
  self._set(digest,'EXECUTING')
  self.call('execute_request',{'operation_id':row[3]})
  return self.reconcile(digest)
 def pending(self):
  return [r[0] for r in self.db.execute("SELECT digest FROM attempts WHERE actor=? AND state NOT IN ('SAVED','FAILED')",(self.actor,))]

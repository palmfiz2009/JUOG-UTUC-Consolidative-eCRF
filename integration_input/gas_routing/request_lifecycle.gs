/* Durable request preparation precedes all business writes. Owned by verified
 * individual, serialized by the enclosing ScriptLock. No browser payload storage. */
function JuogRequestLifecycleV3(d){
 const copy=x=>JSON.parse(JSON.stringify(x));
 const canonical=x=>JSON.stringify(x);
 function subject(){const u=d.user();if(!u||!u.enabled||!u.id)throw Error('AUTH_REQUIRED');return u;}
 function own(s,id,u){const rs=(s.requests||[]).filter(r=>r.id===id);if(rs.length!==1||rs[0].actor!==u.id)throw Error('REQUEST_NOT_VISIBLE');return rs[0];}
 function check(s,r,u){
  const permit=d.authorize(u,r.operation.action,r.operation.payload,d.service.readView().tables);if(!permit.ok)throw Error('REQUEST_NOT_AUTHORIZED');
  const intents=s.intents.filter(i=>i.id===r.id),commits=s.commits.filter(c=>c.id===r.id),events=(s.requestEvents||[]).filter(e=>e.id===r.id);
  if(intents.length>1||commits.length>1)return {state:'UNKNOWN',phase:'CONFLICT'};
  if(intents.length===1){const i=intents[0];if(i.actor!==r.actor||i.action!==r.operation.action||i.request_hash!==d.hash(canonical({action:r.operation.action,payload:r.operation.payload})))return {state:'UNKNOWN',phase:'IDENTITY_MISMATCH'};
   if(commits.length===1){d.service.readView();const audit=s.audits.filter(a=>a.id===r.id);if(audit.length!==1)return {state:'UNKNOWN',phase:'AUDIT_MISSING'};return {state:'SAVED',phase:'COMMITTED',revision:i.revision};}
   return {state:'UNFINISHED',phase:'AUDIT_OR_COMMIT_PENDING'};
  }
  if(commits.length)return {state:'UNKNOWN',phase:'ORPHAN_COMMIT'};
  const failed=events.filter(e=>e.kind==='FAILED');if(failed.length===1)return {state:'FAILED',phase:'REJECTED_BEFORE_INTENT',error:failed[0].error};if(failed.length>1)return {state:'UNKNOWN',phase:'EVENT_CONFLICT'};
  return {state:'UNFINISHED',phase:'PREPARED'};
 }
 function status(id){try{const u=subject(),s=d.store.read(),r=own(s,id,u);return {ok:true,operation_id:id,action:r.operation.action,created_at:r.created_at,...check(s,r,u)};}catch(_){return {ok:false,state:'UNKNOWN',error:'STATUS_UNVERIFIABLE'};}}
 function list(){try{const u=subject(),s=d.store.read();const out=[];for(const r of (s.requests||[]).filter(r=>r.actor===u.id)){let v;try{v=check(s,r,u);}catch(_){v={state:'UNKNOWN',phase:'UNVERIFIABLE'};}out.push({operation_id:r.id,action:r.operation.action,created_at:r.created_at,...v});}return {ok:true,requests:out};}catch(_){return {ok:false,state:'UNKNOWN',error:'STATUS_UNVERIFIABLE'};}}
 function prepare(operation){try{
  const u=subject(),s=d.store.read(),v=d.service.readView();const op=copy(operation);
  if(!d.writeActions.includes(op.action)||!op.payload||typeof op.payload!=='object'||Array.isArray(op.payload))return {ok:false,error:'ACTION_NOT_PREPARABLE'};
  if(typeof op.payload.registration_id==='string')op.payload.registration_id=juogNormalizeRegistrationV3_(op.payload.registration_id);
  if(typeof op.payload.reporter_email==='string')op.payload.reporter_email=juogPythonStripV3_(op.payload.reporter_email);
  const unsafe=(v,depth=0)=>depth>24||(v&&typeof v==='object'&&Object.entries(v).some(([k,x])=>['password','token','identity_assertion','access_token','refresh_token','signing_key','resume_code'].includes(k.toLowerCase())||unsafe(x,depth+1)));
  if(unsafe(op.payload)||d.privacy(op.payload))return {ok:false,error:'DIRECT_IDENTIFIER_NOT_ALLOWED'};
  if(op.action==='save_crf')op.payload=juogNormalizeRequiredReasonV3_(op.payload);
  const permission=d.authorize(u,op.action,op.payload,v.tables);if(!permission.ok)return permission;
  const semantic=copy(op.payload);for(const p of [semantic,semantic.crf_payload||{}]){delete p.submission_id;delete p.submitted_at;}
  const fingerprint=d.hash(canonical({action:op.action,payload:semantic}));
  for(const r of (s.requests||[]).filter(r=>r.actor===u.id)){
   let state;try{state=check(s,r,u).state;}catch(_){state='UNKNOWN';}
   if(state==='UNKNOWN')return {ok:false,error:'UNKNOWN_REQUEST_BLOCKS_NEW_OPERATION'};
   if(state==='UNFINISHED'){if(r.fingerprint===fingerprint)return {ok:true,operation_id:r.id,existing:true};return {ok:false,error:'UNFINISHED_REQUEST_BLOCKS_NEW_OPERATION'};}
  }
  op.id=d.uuid();op.expected_revision=v.revision;
  const r={id:op.id,actor:u.id,created_at:d.now(),fingerprint,operation:op};
  d.store.assertFits(r);d.store.appendRequest(r);
  const saved=own(d.store.read(),op.id,u);if(canonical(saved)!==canonical(r))throw Error('REQUEST_NOT_DURABLE');
  return {ok:true,operation_id:op.id,existing:false};
 }catch(_){return {ok:false,state:'UNKNOWN',error:'PREPARATION_UNCERTAIN'};}}
 function execute(id){try{
  const u=subject(),s=d.store.read(),r=own(s,id,u),state=check(s,r,u);
  if(state.state==='UNKNOWN')return {ok:false,state:'UNKNOWN',error:'RECONCILIATION_REQUIRED'};
  if(state.state==='FAILED')return {ok:false,...state};
  const result=d.service.execute('server-verified',r.operation);
  if(!result.ok){
   const terminal=['STALE_DOMAIN_REVISION','VALIDATION_FAILED','STALE_VERSION','INITIAL_ALREADY_EXISTS','NO_PRIOR_RECORD','INVALID_RECORD_IDENTITY','CORRECTION_REASON_REQUIRED','DIRECT_IDENTIFIER_NOT_ALLOWED'];
   const after=d.store.read();
   if((result.rejected_before_intent===true||terminal.includes(result.error))&&!after.intents.some(i=>i.id===id)&&!(after.requestEvents||[]).some(e=>e.id===id&&e.kind==='FAILED'))d.store.appendRequestEvent({id,kind:'FAILED',actor:u.id,at:d.now(),error:result.error});
   return {...status(id),...result,ok:false}; // never promote a status-read success to save success
  }
  const verified=status(id);if(verified.state!=='SAVED')return {ok:false,state:'UNKNOWN',error:'AUDIT_NOT_CONFIRMED'};
  return {...result,state:'SAVED',operation_id:id};
 }catch(_){return {ok:false,state:'UNKNOWN',error:'EXECUTION_UNCERTAIN'};}}
 return {prepare,status,list,execute};
}

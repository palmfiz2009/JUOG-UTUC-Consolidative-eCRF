/* Append-only migration transaction prototype: underlying legacy sheets stay immutable.
 * Each committed intent contains a materialized view; real storage/size/read adapters
 * and migration approval are required. Never call this on a current clinical ledger.
 */
function JuogDomainServiceV3(deps){
 const copy=x=>JSON.parse(JSON.stringify(x));
 const fail=code=>{const e=Error(code);e.safeCode=code;throw e;};
 const hash=x=>deps.hash(JSON.stringify(x));
 function verify(i,s){const audits=s.audits.filter(a=>a.id===i.id);if(audits.length!==1||audits[0].after_hash!==i.after_hash||audits[0].before_hash!==i.before_hash||audits[0].actor!==i.actor||audits[0].action!==i.action||hash(audits[0].detail||null)!==hash(i.audit_detail||null))fail('DOMAIN_AUDIT_MISMATCH');if(hash(i.after)!==i.after_hash)fail('DOMAIN_VIEW_HASH_MISMATCH');}
 function committed(s){if(s.commits.some(c=>s.commits.filter(x=>x.id===c.id).length!==1||s.intents.filter(i=>i.id===c.id).length!==1))fail('DOMAIN_COMMIT_CONFLICT');return s.intents.filter(i=>s.commits.filter(c=>c.id===i.id).length===1).sort((a,b)=>a.revision-b.revision);}
 function view(s){const done=committed(s);let current=s.baseline,rev=0;for(const i of done){verify(i,s);if(i.revision!==rev+1||i.before_hash!==hash(current))fail('DOMAIN_HISTORY_CONFLICT');current=i.after;rev=i.revision;}return {tables:copy(current),revision:rev};}
 function finish(i,who){let s=deps.store.read();if(s.commits.some(c=>c.id===i.id)){if(s.commits.filter(c=>c.id===i.id).length!==1)fail('DOMAIN_COMMIT_CONFLICT');verify(i,s);return {ok:true,existing:true,revision:i.revision,result:i.result};}let a=s.audits.filter(x=>x.id===i.id);if(a.length>1)fail('DOMAIN_AUDIT_MISMATCH');if(!a.length)deps.store.appendAudit({id:i.id,actor:i.actor,action:i.action,detail:i.audit_detail||null,before_hash:i.before_hash,after_hash:i.after_hash,accepted_at:i.accepted_at,materialized_at:deps.now(),materialized_by:who.id});verify(i,deps.store.read());deps.store.appendCommit({id:i.id,at:deps.now(),by:who.id});s=deps.store.read();if(s.commits.filter(c=>c.id===i.id).length!==1)fail('DOMAIN_COMMIT_CONFLICT');verify(i,s);return {ok:true,existing:false,revision:i.revision,result:i.result};}
 return {execute:function(assertion,operation){try{return deps.withLock(()=>{
  const who=deps.authenticate(assertion);if(!who?.enabled)fail('AUTH_REQUIRED');
  if(!/^[A-Za-z0-9_-]{1,128}$/.test(operation.id||''))fail('OPERATION_ID');
  if(deps.privacy(operation.payload))fail('DIRECT_IDENTIFIER_NOT_ALLOWED');
  const s=deps.store.read(),v=view(s);const authorization=deps.authorize(who,operation.action,operation.payload,v.tables);if(!authorization.ok)fail(authorization.error);
  const h=hash({action:operation.action,payload:operation.payload}),prior=s.intents.filter(i=>i.id===operation.id);
  if(prior.length>1)fail('DOMAIN_INTENT_CONFLICT');if(prior.length){if(prior[0].request_hash!==h||prior[0].actor!==who.id)fail('OPERATION_ID_CONFLICT');return finish(prior[0],who);}
  if(s.intents.length!==committed(s).length)fail('DOMAIN_RECOVERY_REQUIRED');
  if(operation.expected_revision!==v.revision)fail('STALE_DOMAIN_REVISION');
  const planned=deps.plan(operation.action,copy(operation.payload),v.tables,who,operation.id);if(!planned.ok)return {...planned,rejected_before_intent:true};
  // No transport/authentication secrets may be persisted in results.
  const result=copy(planned.result||{});delete result.resume_code;delete result.token;
  const i={id:operation.id,actor:who.id,action:operation.action,request_hash:h,revision:v.revision+1,before_hash:hash(v.tables),after_hash:hash(planned.after),after:planned.after,audit_detail:planned.audit_detail||null,result,accepted_at:deps.now()};
  deps.store.assertFits(i);deps.store.appendIntent(copy(i));const saved=deps.store.read().intents.filter(x=>x.id===i.id);if(saved.length!==1||hash(saved[0])!==hash(i))fail('DOMAIN_INTENT_NOT_DURABLE');return finish(i,who);
 });}catch(e){return {ok:false,error:e.safeCode||'DOMAIN_INCOMPLETE'};}},readView:function(){return view(deps.store.read());}};
}

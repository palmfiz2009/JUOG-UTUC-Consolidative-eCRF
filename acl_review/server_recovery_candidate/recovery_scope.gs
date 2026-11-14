/* Candidate only. Read existing durable requests; never create/update a sheet.
 * Requires separate approval of this narrowly scoped read route before deployment.
 */
function juogCanonicalRecoveryScope_(p){
 if(!p||typeof p!=='object'||Array.isArray(p)||Object.keys(p).sort().join(',')!=='facility_code,record_key,registration_id'||p.registration_id!=='JUOG-971'||p.facility_code!=='TEST01'||p.record_key!=='JUOG-971|perioperative_30d|30d')throw Error('RECOVERY_SCOPE_DENIED');
}
function juogCanonicalRecoveryList_(store,service,lifecycle,who,p,c){
 if(!c||c.sessionExecutionStage!=='AUTH04_APPROVED'||c.canonicalRecoveryReadApproved!==true||typeof c.canonicalRecoveryReviewRef!=='string'||!c.canonicalRecoveryReviewRef.trim())return {ok:false,error:'RECOVERY_READ_NOT_APPROVED'};
 try{
  juogCanonicalRecoveryScope_(p);
  if(!who||!who.enabled||who.role!=='facility'||JSON.stringify(who.facilities)!=='["TEST01"]')throw Error('RECOVERY_SCOPE_DENIED');
  const view=service.readView();
  if(!service.authorize(who,'read_crf',p,view.tables).ok)throw Error('RECOVERY_SCOPE_DENIED');
  const rows=store.read().requests.filter(r=>r.actor===who.id&&r.operation&&r.operation.action==='save_crf'&&r.operation.payload&&r.operation.payload.registration_id===p.registration_id&&r.operation.payload.facility_code===p.facility_code&&r.operation.payload.record_key===p.record_key);
  if(rows.length>100)throw Error('RECOVERY_SCOPE_DENIED');
  const out=[];
  for(const r of rows){
   juogAuth04Operation_(r.operation);
   const body=r.operation.payload;
   if(body.crf_type!=='perioperative_30d'||body.visit!=='30d'||typeof r.id!=='string'||! /^[A-Za-z0-9_-]{1,128}$/.test(r.id)||typeof body.submission_id!=='string'||! /^[A-Za-z0-9_-]{1,128}$/.test(body.submission_id)||!Number.isInteger(body.expected_record_version)||body.expected_record_version<0)throw Error('RECOVERY_STATE_UNVERIFIABLE');
   const status=lifecycle.status(r.id);
   if(status.ok!==true||status.operation_id!==r.id||status.action!=='save_crf'||!['SAVED','FAILED','UNFINISHED'].includes(status.state))throw Error('RECOVERY_STATE_UNVERIFIABLE');
   const phases={SAVED:['COMMITTED'],FAILED:['REJECTED_BEFORE_INTENT'],UNFINISHED:['PREPARED','AUDIT_OR_COMMIT_PENDING']};
   if(!phases[status.state].includes(status.phase))throw Error('RECOVERY_STATE_UNVERIFIABLE');
   // No actor/principal, clinical payload, credentials, raw errors or broad list.
   out.push({operation_id:r.id,state:status.state,phase:status.phase,submission_id:r.operation.payload.submission_id,expected_record_version:r.operation.payload.expected_record_version});
  }
  return {ok:true,read_only:true,record_key:p.record_key,requests:out};
 }catch(_){return {ok:false,error:'RECOVERY_STATE_UNVERIFIABLE'};}
}

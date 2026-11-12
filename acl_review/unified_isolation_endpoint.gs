/* Unified candidate isolation entry, NOT current doPost. No configuration or sheet creation.
 * Requires auth_bridge.gs, privacy_revision2.gs, domain_transaction.gs,
 * domain_sheets_store.gs, admin_routes.gs. All unified routes require separate integration approval.
 * No legacy fallback, no mail, no network calls, no deployment at load. */
function juogUnifiedIsolationEntryV3_(envelope,c) {
 const forbidden=['1R1a55w19qfS7XTa6Ran7EnuTNZpFkGoXIFfqesv7zoc','1XEKihUvJBHP4BZNf8WMf14__zsiiZgY8ozFnhw_NZNE','1XaLdVGN39skmXVhiyPN-uOb9B8zjo3rmbNgYZCndJRs'];
 if(!c||c.environment!=='ISOLATED_TEST'||!c.approvalRef||c.backupVerified!==true||c.qaApproved!==true||c.fictionalBaselineVerified!==true||c.notificationsDisabled!==true||!c.spreadsheetId||c.spreadsheetId!==c.approvedSpreadsheetId||forbidden.includes(c.spreadsheetId))return {ok:false,error:'ISOLATION_NOT_APPROVED'};
 if(c.sessionPolicy==='isolated_gas_session_b2'&&(c.spreadsheetId!=='1Hd6EHDPZe8zGcDbILkaBLubgF5atfAzRfpPSN5LemiU'||ScriptApp.getScriptId()!=='11wSp4ePaP5b5A2b5ITZZSZa3YTe-Ex-Tu6oGlEkkRfkPrMCA4deVSZDy'))return {ok:false,error:'ISOLATION_NOT_APPROVED'};
 const authConnect=c.sessionPolicy==='isolated_gas_session_b2'&&c.sessionExecutionStage==='AUTH_CONNECT';
 if(c.sessionPolicy==='isolated_gas_session_b2'&&!['AUTH_CONNECT','AUTH04_APPROVED'].includes(c.sessionExecutionStage))return {ok:false,error:'ISOLATION_NOT_APPROVED'};
 if(authConnect&&(c.authConnectReviewApproved!==true||typeof c.authConnectReviewRef!=='string'||!c.authConnectReviewRef.trim()))return {ok:false,error:'AUTH_CONNECT_NOT_APPROVED'};
 const lock=LockService.getScriptLock();if(!lock.tryLock(30000))return {ok:false,error:'LOCK_TIMEOUT'};
 try {
  const auth=juogV3DecodeBridge_(envelope,c),req=auth.request;
  if(!authConnect&&(c.allRoutesReviewed!==true||c.schemaParityApproved!==true))return {ok:false,error:'INTEGRATION_NOT_APPROVED'};
  const control=['session_revoke','prepare_request','request_status','list_requests','execute_request'];
  let op=req.payload;if(!op||(!control.includes(req.action)&&op.action!==req.action))return {ok:false,error:'ACTION_MISMATCH'};
  const ss=SpreadsheetApp.openById(c.spreadsheetId),who=juogV3ReadIndividualAcl_(ss,auth.principal.issuer,auth.principal.subject);
  if(authConnect&&req.action!=='session_revoke'&&(!who||who.role!=='facility'))return {ok:false,error:'ACL_DENIED'};
  const gate=c.sessionPolicy==='isolated_gas_session_b2'?juogSessionGateB2_(ss,c,auth,who):null;
  if(gate&&gate.response)return gate.response;
  if(gate&&c.sessionExecutionStage!=='AUTH04_APPROVED'&&req.action!=='ui_context')return {ok:false,error:'AUTH04_EXECUTION_NOT_APPROVED'};
  if(gate&&c.sessionExecutionStage==='AUTH04_APPROVED'&&!c.auth04ExecutionApprovalRef)return {ok:false,error:'AUTH04_EXECUTION_NOT_APPROVED'};
  // Authentication scope returns before creating any business store/service or
  // reading business data. Business approvals and business secrets stay unset.
  if(authConnect){
   if(!op.payload||typeof op.payload!=='object'||Array.isArray(op.payload)||
      Object.keys(op.payload).some(k=>k!=='registration_id')||
      (op.payload.registration_id!==undefined&&op.payload.registration_id!==''))return {ok:false,error:'AUTH_CONNECT_CONTEXT_ONLY'};
   gate.guard();
   return {ok:true,backend_version:'b2-auth-connect',environment:'TEST',isolation:true,
    role:who.role,user_id:who.id,facilities:who.facilities,facility_code:'TEST01',
    execution_stage:'AUTH_CONNECT',business_writes_allowed:false};
  }
  const hash=s=>Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256,s,Utilities.Charset.UTF_8).map(b=>('0'+((b+256)%256).toString(16)).slice(-2)).join('');
  const store=juogDomainSheetsStoreV3_(ss,hash,()=>Utilities.getUuid(),gate?gate.guard:null);
  if(gate){
   for(const name of ['appendIntent','appendAudit','appendCommit','appendRequest','appendRequestEvent']){
    const original=store[name];store[name]=function(value){gate.guard();return original(value);};
   }
  }
  if(req.action==='execute_request'){
   const found=store.read().requests.filter(r=>r.id===req.payload.operation_id&&who&&r.actor===who.id);
   if(found.length!==1)return {ok:false,state:'UNKNOWN',error:'REQUEST_NOT_VISIBLE'};
   op=found[0].operation;
  }
  const mac=s=>Utilities.computeHmacSha256Signature(s,c.resumeDerivationKey,Utilities.Charset.UTF_8);
  if(typeof c.resumeDerivationKey!=='string'||c.resumeDerivationKey.length<32||typeof c.draftPepper!=='string'||c.draftPepper.length<32)throw Error('KEY_NOT_CONFIGURED');
  const code=()=>{const bytes=mac('resume-v3|'+who.id+'|'+op.id);let n=0;for(let i=0;i<6;i++)n=n*256+(bytes[i]&255);return String(n%1000000).padStart(6,'0');};
  const codeHash=s=>Utilities.base64EncodeWebSafe(Utilities.computeHmacSha256Signature(s,c.draftPepper,Utilities.Charset.UTF_8)).replace(/=+$/g,'');
  const assignmentSheet=ss.getSheetByName('V3_Assignments');
  const assignments=u=>{if(!assignmentSheet)return [];const rows=assignmentSheet.getDataRange().getValues(),ix=Object.fromEntries(rows[0].map((k,i)=>[k,i]));if(['user_id','role','screening_id','enabled'].some(k=>ix[k]===undefined))throw Error('ASSIGNMENT_SCHEMA');return rows.slice(1).filter(r=>r[ix.user_id]===u.id&&r[ix.role]===u.role&&(r[ix.enabled]===true||r[ix.enabled]==='TRUE')).map(r=>r[ix.screening_id]);};
  let BusinessDate=Date;
  if(c.businessTestNow){
   if(!c.timeControlApprovalRef||!Number.isFinite(new Date(c.businessTestNow).getTime()))throw Error('TIME_CONTROL_NOT_APPROVED');
   const fixed=new Date(c.businessTestNow).getTime();BusinessDate=class extends Date{constructor(...args){super(...(args.length?args:[fixed]));}static now(){return fixed;}};
  }
  const service=new JuogUnifiedDomainV3({store,hash,now:()=>new Date().toISOString(),today:()=>Utilities.formatDate(new BusinessDate(),'Asia/Tokyo','yyyy-MM-dd'),withLock:f=>f(),privacy:containsDirectIdentifier_,redact:stripDirectIdentifiers_,validate:validateClinicalV3,authenticate:()=>who,assignments,
   legacyPlan:(a,p,t)=>juogLegacyPlanV3_(a,p,t,{Date:BusinessDate,utilities:Utilities,draftPepper:c.draftPepper}),
   adminRuntime:(u,id)=>({now:()=>new Date().toISOString(),privacy:containsDirectIdentifier_,resumeCode:code,codeHash,voidPolicyApproved:c.voidPolicyApproved===true})});

  if(req.action==='ui_context'){
   if(!who||!who.enabled)return {ok:false,error:'AUTH_REQUIRED'};
   const v=service.readView();let facility=null;
   if(op.payload&&op.payload.registration_id){const h=v.tables.Registry[0],ix=Object.fromEntries(h.map((k,i)=>[k,i]));const matches=v.tables.Registry.slice(1).filter(r=>r[ix.registration_id]===op.payload.registration_id&&who.facilities.includes(r[ix.facility_code]));if(matches.length!==1)return {ok:false,error:'SUBJECT_FORBIDDEN'};facility=matches[0][ix.facility_code];}
   return {ok:true,backend_version:'v3-unified-review',environment:'TEST',isolation:true,role:who.role,user_id:who.id,facilities:who.facilities,facility_code:facility,revision:v.revision,pending:store.read().intents.length!==store.read().commits.length};
  }
  const writes=['submit_screening','submit_mdt_review','finalize_mdt','save_screening_draft','delete_screening_draft','save_draft','delete_draft','reset_draft_code','update_draft_email','void_registration','save_crf'];
  const lifecycle=new JuogRequestLifecycleV3({user:()=>who,store,service,authorize:service.authorize,privacy:containsDirectIdentifier_,hash,uuid:()=>Utilities.getUuid(),now:()=>new Date().toISOString(),writeActions:writes});
  if(req.action==='prepare_request')return lifecycle.prepare(req.payload);
  if(req.action==='request_status')return lifecycle.status(req.payload.operation_id);
  if(req.action==='list_requests')return lifecycle.list();
  if(writes.includes(req.action))return {ok:false,error:'DURABLE_PREPARATION_REQUIRED'};
  const response=req.action==='execute_request'?lifecycle.execute(req.payload.operation_id):service.execute(envelope.identity_assertion,op);

  if(response.ok&&op.action==='reset_draft_code'){
   // Reveal only to the same currently-authorized actor after durable commit, and
   // only while this operation's code remains current. Do not log this response.
   const tables=service.readView().tables,d=tables.CRF_Drafts,di=Object.fromEntries(d[0].map((h,i)=>[h,i]));
   const key=[op.payload.registration_id,op.payload.crf_type,op.payload.visit].join('|'),rows=d.slice(1).filter(r=>r[di.draft_key]===key);
   if(rows.length===1&&rows[0][di.resume_code_hash]===codeHash(code()))response.resume_code=code();
   else response.code_delivery='SUPERSEDED';
  }
  return response;
 }catch(e){const safe=['AUTH_REQUIRED','AUTH_INVALID','AUTH_EXPIRED','REQUEST_SIGNATURE_MISMATCH','SESSION_REQUIRED','SESSION_INVALID','SESSION_REVOKED','ASSERTION_REPLAY','SESSION_STORE_UNAVAILABLE','SESSION_STORE_INVALID','SESSION_STORE_FULL','ACL_DENIED','ACL_CHANGED'];return {ok:false,error:safe.includes(e.message)?e.message:'UNIFIED_TRANSACTION_INCOMPLETE'};}finally{lock.releaseLock();}
}

/* PR15 candidate for the EXISTING undeployed project. Never run setupRegistry.+ * Disabled without separately provisioned approval/configuration and precreated tabs.
 * One project, one outer ScriptLock. Legacy token routing is absent from doPost.
 */
let JUOG_PR15_GUARD_ = null;
// A handle only, never cached cell values or authorization decisions. Lifetime is
// one locked request; getSpreadsheet_ still checks the configured workbook ID.
let JUOG_PR15_WORKBOOK_ = null;
const PR15_SCRIPT_='1_oVuL1i6Kmyu5egp-iDHIku-nN5JxoQ1ySPSluAsNc2gCFXGvBSJGDAR';
const PR15_SHEET_='1XaLdVGN39skmXVhiyPN-uOb9B8zjo3rmbNgYZCndJRs';
const PR15_STAGE_='PR15_ISOLATED_CRFS';
function pr15Hash_(s){return Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256,s,Utilities.Charset.UTF_8).map(b=>('0'+((b+256)%256).toString(16)).slice(-2)).join('');}
// Reuse service object handles within one locked request only. Every caller
// still reads live cells; never retain ACL, ownership, header or record values.
function pr15WorkbookHandles_(raw){
 const sheets=new Map();
 return {
  getId:()=>raw.getId(), getName:()=>raw.getName(),
  getSheetByName:name=>{
   if(sheets.has(name))return sheets.get(name);
   const sheet=raw.getSheetByName(name);
   if(sheet)sheets.set(name,sheet);
   return sheet;
  }
 };
}
function pr15Rows_(ss,name,required){
 const sh=ss.getSheetByName(name);if(!sh)throw Error('SCHEMA_MISSING');
 const rows=sh.getDataRange().getValues(),h=rows[0]||[];
 if(new Set(h).size!==h.length||required.some(k=>!h.includes(k)))throw Error('SCHEMA_INVALID');
 return {sh,rows:rows.slice(1).map(r=>Object.fromEntries(h.map((k,i)=>[k,r[i]])))};
}
function pr15Pair_(p,draft){
 return p.crf_type==='perioperative_30d'&&p.visit==='30d'||p.crf_type==='day90'&&p.visit==='90d'||
  p.crf_type==='followup'&&(draft?p.visit==='followup':['6m','9m','12m','15m','18m','21m','24m'].includes(p.visit));
}
function pr15Records_(ss,id){
 let rows=[];
 for(const name of ['CRF_30d','CRF_90d','CRF_Followup'])rows=rows.concat(pr15Rows_(ss,name,['submission_id','record_key','record_version','registration_id','facility_code','payload_json']).rows.filter(r=>r.registration_id===id));
 const versions={};
 for(const [t,vs] of [['perioperative_30d',['30d']],['day90',['90d']],['followup',['6m','9m','12m','15m','18m','21m','24m']]])for(const v of vs)versions[[id,t,v].join('|')]=0;
 for(const key of Object.keys(versions)){
  const records=rows.filter(r=>r.record_key===key),numbers=records.map(r=>Number(r.record_version)).sort((a,b)=>a-b);
  if(numbers.some((v,i)=>!Number.isInteger(v)||v!==i+1))throw Error('VERSION_STORE_INVALID');
  versions[key]=records.length;
 }
 return {rows,versions};
}
function pr15Owner_(ss,who,p){
 if(!who||!who.enabled||who.role!=='facility'||JSON.stringify(who.facilities)!=='["TEST01"]')throw Error('ACL_DENIED');
 if(typeof p.registration_id!=='string'||!/^JUOG-\d{3,4}$/.test(p.registration_id))throw Error('SUBJECT_FORBIDDEN');
 if(p.facility_code&&p.facility_code!=='TEST01')throw Error('SUBJECT_FORBIDDEN');
 if(['actor','actor_auth','user_id','role','token'].some(k=>k in p))throw Error('ACTOR_OVERRIDE_DENIED');
 const owners=pr15Rows_(ss,'R1_CaseOwners',['registration_id','facility_code','user_id','enabled']).rows.filter(r=>r.registration_id===p.registration_id);
 if(owners.length!==1||owners[0].user_id!==who.id||owners[0].facility_code!=='TEST01'||![true,'TRUE'].includes(owners[0].enabled))throw Error('SUBJECT_FORBIDDEN');
 const reg=pr15Rows_(ss,'Registry',['registration_id','facility_code','status']).rows.filter(r=>r.registration_id===p.registration_id);
 if(reg.length!==1||reg[0].facility_code!=='TEST01'||reg[0].status!=='ACTIVE')throw Error('SUBJECT_FORBIDDEN');
}
function pr15Journal_(ss,guard){
 const table=()=>pr15Rows_(ss,'R1_Operations',['sequence','event_json','digest']);
 function decode(t){return t.rows.map((r,i)=>{
  if(r.sequence!==i+1||r.digest!==pr15Hash_(r.event_json))throw Error('OPERATION_STORE_INVALID');
  const e=JSON.parse(r.event_json);if(!['INTENT','COMMIT'].includes(e.kind)||!e.uuid||!e.actor||!e.key||!e.digest)throw Error('OPERATION_STORE_INVALID');return e;
 });}
 function read(){return decode(table());}
 function append(e){guard();const before=table(),old=decode(before),seq=old.length+1,json=JSON.stringify(e);before.sh.appendRow([seq,json,pr15Hash_(json)]);SpreadsheetApp.flush();const after=read();if(after.length!==seq||JSON.stringify(after[seq-1])!==json)throw Error('OPERATION_WRITE_UNCONFIRMED');guard();}
 return {read,append};
}
function juogPr15Entry_(envelope,c){
 if(!c||c.enabled!==true||c.stage!==PR15_STAGE_||c.scriptId!==PR15_SCRIPT_||c.spreadsheetId!==PR15_SHEET_||
  ScriptApp.getScriptId()!==PR15_SCRIPT_||c.notificationsDisabled!==true||c.sessionPolicy!=='isolated_gas_session_b2'||
  c.sessionStoreApproved!==true||c.bridgeIssuer!=='JUOG_PR15_FIXTURE'||c.audience!=='JUOG_PR15_GAS'||c.oidcIssuer!=='https://accounts.google.com'||
  !c.sessionStoreGeneration||c.sessionStoreGeneration==='d72bcf33-423d-4c4d-862d-2e2d69bc3edf'||
  ['qaRef','piRef','singleWriterRef','backupRef','b2PolicyRef'].some(k=>typeof c[k]!=='string'||!c[k].trim())||
  PropertiesService.getScriptProperties().getProperty('SPREADSHEET_ID')!==PR15_SHEET_)return {ok:false,error:'INTEGRATION_NOT_APPROVED'};
 const lock=LockService.getScriptLock();if(!lock.tryLock(30000))return {ok:false,error:'LOCK_TIMEOUT'};
 try{
  const auth=juogV3DecodeBridge_(envelope,c);let a=auth.request.action,p=auth.request.payload;
  if(!p||typeof p!=='object'||Array.isArray(p))throw Error('REQUEST_INVALID');
  if('staged_save' in p && (typeof p.staged_save!=='boolean'||!['save_crf','recovery_retry'].includes(a)))throw Error('REQUEST_INVALID');
  const staged=p.staged_save===true;
  const allowed=['ui_context','session_revoke','backend_info','validate','get_crf_linkage','save_crf','save_draft','get_draft','delete_draft','read_crf','request_status','recovery_status','recovery_retry','get_sections','save_section'];
  if(!allowed.includes(a))throw Error('ROUTE_DENIED');
  const ss=pr15WorkbookHandles_(SpreadsheetApp.openById(c.spreadsheetId)),who=juogV3ReadIndividualAcl_(ss,auth.principal.issuer,auth.principal.subject);
  JUOG_PR15_WORKBOOK_={id:c.spreadsheetId,ss};
  const gate=juogSessionGateB2_(ss,c,auth,who);
  const bind=r=>Object.assign(r,{spreadsheet_id:c.spreadsheetId,script_id:c.scriptId,integration_stage:PR15_STAGE_,generation:c.sessionStoreGeneration,role:who&&who.role,facility_code:'TEST01'});
  if(gate.response)return bind(gate.response);
  if(!who||!who.enabled||who.role!=='facility'||JSON.stringify(who.facilities)!=='["TEST01"]')throw Error('ACL_DENIED');
  JUOG_PR15_GUARD_=gate.guard;
  const respond=r=>{JUOG_PR15_GUARD_();return bind(r);};
  if(a==='ui_context'||a==='backend_info'){
   if(Object.keys(p).length)throw Error('REQUEST_INVALID');
   return respond({ok:true,backend_version:BACKEND_VERSION,user_id:who.id,facilities:who.facilities,business_writes_allowed:true,environment:'TEST'});
  }
  let q=a==='save_crf'?p.payload:p; if(!q||typeof q!=='object'||Array.isArray(q))throw Error('REQUEST_INVALID');
  pr15Owner_(ss,who,q);
  JUOG_PR15_GUARD_=()=>{gate.guard();pr15Owner_(ss,who,q);};
  if(['save_crf','save_draft'].includes(a)){
   if(q.facility_code!=='TEST01')throw Error('SUBJECT_FORBIDDEN');
   if(q.reporter_email!=='fictional@example.invalid')throw Error('FICTIONAL_CONTACT_REQUIRED');
  }
  const journal=pr15Journal_(ss,JUOG_PR15_GUARD_),history=journal.read();
  if(a==='get_sections'||a==='save_section'){
   const dk=[q.registration_id,q.crf_type,q.visit].join('|');
   if(history.some(e=>e.kind==='INTENT'&&e.key===dk&&!history.some(x=>x.uuid===e.uuid&&x.kind==='COMMIT')))throw Error('PENDING_OPERATION');
   return respond(pr15SectionDraft_(ss,who,q,a,JUOG_PR15_GUARD_));
  }
  if(a==='request_status'){
   const matches=history.filter(e=>e.uuid===p.submission_id);
   if(!matches.length)return respond({ok:true,state:'UNKNOWN'});
   if(matches.some(e=>e.actor!==who.id||!e.key.startsWith(p.registration_id+'|')))throw Error('SUBJECT_FORBIDDEN');
   const commits=matches.filter(e=>e.kind==='COMMIT');
   if(commits.length>1)throw Error('OPERATION_STORE_INVALID');
   return respond({ok:true,state:commits.length?'COMMITTED_RECHECK_REQUIRED':'UNCONFIRMED',receipt:commits.length?commits[0].receipt:null});
  }
  if(a==='recovery_status'||a==='recovery_retry'){
   if(Object.keys(p).some(k=>!['registration_id','facility_code','crf_type','visit','submission_id',...(a==='recovery_retry'?['staged_save']:[])].includes(k)))throw Error('REQUEST_INVALID');
   if(!pr15Pair_(q,false))throw Error('VISIT_INVALID');
   const recovery=pr15Recovery_(ss,journal,who,q);
   if(a==='recovery_status')return respond({ok:true,recovery});
   const selected=recovery.operations.filter(x=>x.uuid===p.submission_id);
   if(recovery.state!=='RETRY_ALLOWED'||selected.length!==1||selected[0].state!=='RETRY_ALLOWED')throw Error('RECOVERY_RECONCILIATION_REQUIRED');
   const original=history.filter(e=>e.kind==='INTENT'&&e.uuid===p.submission_id&&e.actor===who.id);
   if(original.length!==1||!original[0].payload||pr15Hash_(JSON.stringify(original[0].payload))!==original[0].digest)throw Error('RECOVERY_RECONCILIATION_REQUIRED');
   q=JSON.parse(JSON.stringify(original[0].payload));p={payload:q,expected_record_version:original[0].expected,staged_save:staged};a='save_crf';
   pr15Owner_(ss,who,q);
  }
  const records=pr15Records_(ss,q.registration_id);
  if(a==='validate')return respond(Object.assign(validateSubject_(q),{record_versions:records.versions}));
  if(a==='get_crf_linkage')return respond(getCrfLinkage_(q));
  if(a==='read_crf'){
   if(!pr15Pair_(q,false))throw Error('VISIT_INVALID');
   const key=[q.registration_id,q.crf_type,q.visit].join('|');
   return respond({ok:true,record_key:key,record_version:records.versions[key],records:records.rows.filter(r=>r.record_key===key)});
  }
  if(a!=='save_crf'){
   if(!pr15Pair_(q,true))throw Error('VISIT_INVALID');
   // Bind draft to original principal even after a case assignment is transferred.
   pr15Rows_(ss,'CRF_Drafts',CRF_DRAFT_HEADERS);
   if(containsDirectIdentifier_(q))throw Error('DIRECT_IDENTIFIER_NOT_ALLOWED');
   const key=[q.registration_id,q.crf_type,q.visit].join('|');
   const owners=pr15Rows_(ss,'R1_DraftOwners',['draft_key','user_id']);
   const own=owners.rows.filter(r=>r.draft_key===key);
   if(own.length>1||own.length===1&&own[0].user_id!==who.id)throw Error('SUBJECT_FORBIDDEN');
   const before=pr15Rows_(ss,'CRF_Drafts',CRF_DRAFT_HEADERS).rows.filter(r=>r.draft_key===key);
   if(before.length>1||before.length&&!own.length)throw Error('UNTRACKED_DRAFT');
   if(!own.length&&a==='save_draft'){
    gate.guard();owners.sh.appendRow([key,who.id]);SpreadsheetApp.flush();
    const check=pr15Rows_(ss,'R1_DraftOwners',['draft_key','user_id']).rows.filter(r=>r.draft_key===key);
    if(check.length!==1||check[0].user_id!==who.id)throw Error('DRAFT_WRITE_UNCONFIRMED');
   }
   gate.guard();
   const result=({save_draft:saveDraft_UnderLock_,get_draft:getDraft_UnderLock_,delete_draft:deleteDraft_UnderLock_})[a](q);
   if(result.ok&&a!=='get_draft'){
    const after=pr15Rows_(ss,'CRF_Drafts',CRF_DRAFT_HEADERS).rows.filter(r=>r.draft_key===key);
    if(a==='delete_draft'?after.length!==0:after.length!==1||after[0].draft_json!==JSON.stringify(q.draft_state))throw Error('DRAFT_WRITE_UNCONFIRMED');
    const audit=pr15Rows_(ss,'R1_DraftEvents',['event_json','digest']);
    const event=JSON.stringify({action:a,key,actor:who.id,at:new Date().toISOString(),digest:pr15Hash_(JSON.stringify(q))});
    gate.guard();audit.sh.appendRow([event,pr15Hash_(event)]);SpreadsheetApp.flush();
    const verified=pr15Rows_(ss,'R1_DraftEvents',['event_json','digest']).rows;
    if(verified.length!==audit.rows.length+1||verified[verified.length-1].event_json!==event)throw Error('DRAFT_AUDIT_UNCONFIRMED');
   }
   return respond(result);
  }
  if(Object.keys(p).some(k=>!['payload','expected_record_version','staged_save'].includes(k)))throw Error('REQUEST_INVALID');
  if(!pr15Pair_(q,false))throw Error('VISIT_INVALID');
  const key=[q.registration_id,q.crf_type,q.visit].join('|'),uuid=q.submission_id;
  if(q.record_key!==key||typeof uuid!=='string'||!uuid.trim()||!Number.isInteger(p.expected_record_version)||p.expected_record_version<0)throw Error('SUBMISSION_METADATA_INVALID');
  if(!['初回報告','訂正報告'].includes(q.submission_kind)||!q.data||typeof q.data!=='object'||Array.isArray(q.data)||!Object.keys(q.data).length)throw Error('PAYLOAD_INVALID');
  if(containsDirectIdentifier_(q))throw Error('DIRECT_IDENTIFIER_NOT_ALLOWED');
  const clinical=juogClinicalValidate_(q);
  if(!clinical.ok)return respond({ok:false,error:'CLINICAL_VALIDATION_FAILED',validation:clinical});
  const digest=pr15Hash_(JSON.stringify(q)),mine=history.filter(e=>e.uuid===uuid),intents=mine.filter(e=>e.kind==='INTENT'),commits=mine.filter(e=>e.kind==='COMMIT');
  if(intents.length>1||commits.length>1||commits.length&&!intents.length)throw Error('OPERATION_STORE_INVALID');
  if(mine.some(e=>e.actor!==who.id||e.key!==key||e.digest!==digest||e.expected!==p.expected_record_version))throw Error('SUBMISSION_ID_CONFLICT');
  if(commits.length&&records.rows.filter(r=>r.submission_id===uuid&&r.record_key===key&&r.payload_json===JSON.stringify(q)).length!==1)throw Error('COMMITTED_RECORD_MISSING');
  if(!intents.length){
   if(records.rows.some(r=>r.submission_id===uuid))throw Error('UNTRACKED_SUBMISSION');
   if(history.some(e=>e.kind==='INTENT'&&e.key===key&&!history.some(x=>x.uuid===e.uuid&&x.kind==='COMMIT')))throw Error('PENDING_OPERATION');
   if(records.versions[key]!==p.expected_record_version)throw Error('VERSION_CONFLICT');
   if(q.submission_kind==='初回報告'&&p.expected_record_version!==0||q.submission_kind==='訂正報告'&&(p.expected_record_version===0||!String(q.correction_reason||'').trim()))throw Error('VERSION_KIND_INVALID');
   const validation=validateCrfHardStops_(q,validateSubject_(q));if(!validation.ok)return respond(validation);
   const linkage=validateDay90SourceLink_(q);if(!linkage.ok)return respond(linkage);
   journal.append({kind:'INTENT',uuid,key,digest,payload:JSON.parse(JSON.stringify(q)),actor:who.id,facility:'TEST01',expected:p.expected_record_version,at:new Date().toISOString()});
   // No success receipt until body, audit and COMMIT are independently verified.
   // A fresh signed request must resume the server-held canonical UUID.
   if(staged)return respond({ok:false,error:'SAVE_PENDING'});
  }
  gate.guard();
  const result=saveCrf_UnderLock_({payload:q});
  if(!result.ok)return respond(result);
  if(result.record_version!==p.expected_record_version+1||result.audit_verified!==true)throw Error('RECEIPT_MISMATCH');
  if(staged&&!commits.length&&!records.rows.some(r=>r.submission_id===uuid))return respond({ok:false,error:'SAVE_PENDING'});
  if(!commits.length)journal.append({kind:'COMMIT',uuid,key,digest,actor:who.id,facility:'TEST01',expected:p.expected_record_version,at:new Date().toISOString(),receipt:result});
  return respond(result);
 }catch(e){
  const safe=['AUTH_REQUIRED','AUTH_INVALID','AUTH_EXPIRED','REQUEST_SIGNATURE_MISMATCH','SESSION_REQUIRED','SESSION_INVALID','SESSION_REVOKED','ASSERTION_REPLAY','SESSION_STORE_UNAVAILABLE','SESSION_STORE_INVALID','SESSION_STORE_FULL','ACL_DENIED','ACL_CHANGED','SUBJECT_FORBIDDEN','ACTOR_OVERRIDE_DENIED','ROUTE_DENIED','REQUEST_INVALID','VISIT_INVALID','SUBMISSION_METADATA_INVALID','PAYLOAD_INVALID','DIRECT_IDENTIFIER_NOT_ALLOWED','SUBMISSION_ID_CONFLICT','VERSION_CONFLICT','VERSION_KIND_INVALID','PENDING_OPERATION','UNTRACKED_SUBMISSION','SCHEMA_MISSING','SCHEMA_INVALID','VERSION_STORE_INVALID','OPERATION_STORE_INVALID','OPERATION_WRITE_UNCONFIRMED','RECEIPT_MISMATCH'];
  return {ok:false,error:safe.concat(['UNTRACKED_DRAFT','DRAFT_WRITE_UNCONFIRMED','DRAFT_AUDIT_UNCONFIRMED','COMMITTED_RECORD_MISSING','FICTIONAL_CONTACT_REQUIRED','RECOVERY_RECONCILIATION_REQUIRED','DRAFT_STORE_INVALID','DRAFT_CONFLICT','DRAFT_DATA_INVALID']).includes(e.message)?e.message:'TRANSACTION_UNCONFIRMED'};
 }finally{JUOG_PR15_GUARD_=null;JUOG_PR15_WORKBOOK_=null;lock.releaseLock();}
}

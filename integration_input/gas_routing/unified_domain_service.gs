/* Unified domain bridge candidate. One durable domain journal for all materialized
 * business views and the CRF transaction state. No legacy live writes/fallback.
 * Only server-verified identities, assignments and settings may enter deps. */
function JuogUnifiedDomainV3(deps) {
 const clone=x=>JSON.parse(JSON.stringify(x));
 const facilityActions=['submit_screening','save_screening_draft','get_screening_draft','delete_screening_draft','save_draft','get_draft','delete_draft','get_crf_linkage','validate','save_crf','read_crf'];
 const reviewerActions=['list_review_cases','get_screening_crf','get_own_review','submit_mdt_review'];
 const adminActions=['list_screenings','get_screening','finalize_mdt','get_mdt_reviews','reset_draft_code','update_draft_email','stats','void_registration'];
 const objects=(t,n)=>{const rows=t[n];if(!rows)return [];return rows.slice(1).map(r=>Object.fromEntries(rows[0].map((k,i)=>[k,r[i]])));};
 const draftKey=p=>p.registration_id?[p.registration_id,p.crf_type,p.visit].join('|'):'PREMDT-'+deps.hash(String(p.facility_code||'').trim().toUpperCase()+'|'+String(p.local_subject_code||'').trim()).slice(0,24).toUpperCase()+'|screening|mdt_application';
 function authorize(u,a,p,t){
  const no=error=>({ok:false,error});if(!u||!u.enabled||!u.id||!Array.isArray(u.facilities))return no('AUTH_REQUIRED');
  if(!p||typeof p!=='object'||Array.isArray(p))return no('PAYLOAD_REQUIRED');
  if(['admin_user','actor_auth','actor_id','reviewer_name'].some(k=>k in p))return no('CALLER_ACTOR_FORBIDDEN');
  const regs=objects(t,'Registry'),screens=objects(t,'Screening');
  if(u.role==='facility'){
   if(!facilityActions.includes(a))return no('ROLE_NOT_ALLOWED');
   if(!p.facility_code||!u.facilities.includes(p.facility_code))return no('FACILITY_FORBIDDEN');
   if(p.registration_id){const found=regs.filter(r=>r.registration_id===p.registration_id);if(found.length!==1||found[0].facility_code!==p.facility_code||found[0].status!=='ACTIVE')return no('SUBJECT_FORBIDDEN');}
   if(a.includes('draft')){const key=draftKey(p),existing=objects(t,'CRF_Drafts').some(r=>r.draft_key===key),owner=(t.V3_DraftOwners||{})[key];if((owner&&owner!==u.id)||(existing&&!owner))return no('DRAFT_OWNER_REQUIRED');}
  } else if(['radiology','medical_oncology','urology'].includes(u.role)) {
   if(!reviewerActions.includes(a)&&a!=='get_mdt_reviews')return no('ROLE_NOT_ALLOWED');
   if(p.reviewer_role&&p.reviewer_role!==u.role)return no('REVIEW_ROLE_MISMATCH');
   if(a!=='list_review_cases'&&!deps.assignments(u).includes(p.screening_id))return no('REVIEW_ASSIGNMENT_REQUIRED');
   if(a!=='list_review_cases'&&!screens.some(s=>s.screening_id===p.screening_id&&u.facilities.includes(s.facility_code)))return no('FACILITY_FORBIDDEN');
  } else if(u.role==='admin'){
   if(!adminActions.includes(a))return no('ROLE_NOT_ALLOWED');
   if(p.screening_id&&!screens.some(s=>s.screening_id===p.screening_id&&u.facilities.includes(s.facility_code)))return no('FACILITY_FORBIDDEN');
   if(p.registration_id&&!regs.some(s=>s.registration_id===p.registration_id&&u.facilities.includes(s.facility_code)))return no('FACILITY_FORBIDDEN');
  } else return no('ROLE_NOT_ALLOWED');
  return {ok:true};
 }
 function scoped(t,u){const copy=clone(t);for(const n of ['Registry','Screening']){const h=copy[n][0],fi=h.indexOf('facility_code');copy[n]=[h,...copy[n].slice(1).filter(r=>u.facilities.includes(r[fi]))];}return copy;}
 function crfPlan(a,p,t,u){
  const after=clone(t),state=after.V3_CrfState||{intents:[],records:[],audits:[],events:[]};
  // Historical rows require separate reconciliation: never synthesize old intents.
  const legacy=['CRF_30d','CRF_90d','CRF_Followup'].flatMap(n=>objects(t,n));
  const service=new JuogSaveServiceV3({verifyIdentity:()=>({issuer:'verified-server',subject:u.id}),directory:()=>u,
   registry:id=>{const r=objects(t,'Registry').find(x=>x.registration_id===id);return r&&{status:r.status,facility_code:r.facility_code,registration_date:String(r.registered_at).slice(0,10),consent_date:String(r.consent_date).slice(0,10)};},
   hash:deps.hash,privacy:deps.privacy,redact:deps.redact,validate:deps.validate,today:deps.today,now:deps.now,withLock:f=>f(),
   store:{read:()=>clone(state),assertFits:()=>{},appendIntent:i=>state.intents.push(clone(i)),appendRecord:r=>state.records.push(clone(r)),appendAudit:a=>state.audits.push(clone(a)),appendEvent:e=>state.events.push(clone(e))}});
  if(a==='save_crf'&&legacy.some(r=>r.record_key===p.record_key)&&!state.intents.some(i=>i.record.record_key===p.record_key))return {ok:false,error:'LEGACY_RECONCILIATION_REQUIRED'};
  const result=a==='save_crf'?service.save('verified',p):service.read('verified',p.record_key);
  if(!result.ok)return result;
  if(a==='save_crf'||t.V3_CrfState)after.V3_CrfState=state;
  // Materialize only newly created records/audits to the same visible business views.
  for(const record of state.records){
   const payload=record.payload,n={perioperative_30d:'CRF_30d',day90:'CRF_90d',followup:'CRF_Followup'}[payload.crf_type];
   if(!n||!after[n]||!after.CRFSubmissionAudit)return {ok:false,error:'CRF_VIEW_SCHEMA'};
   const values={...payload,saved_at:record.accepted_at,record_version:record.record_version,payload_json:JSON.stringify(payload)};
   const av={...values,sheet_name:n},expectedRow=after[n][0].map(k=>values[k]??''),expectedAudit=after.CRFSubmissionAudit[0].map(k=>av[k]??'');
   const ri=after[n][0].indexOf('submission_id'),ai=after.CRFSubmissionAudit[0].indexOf('submission_id');
   const rows=after[n].slice(1).filter(r=>r[ri]===record.submission_id),audits=after.CRFSubmissionAudit.slice(1).filter(r=>r[ai]===record.submission_id);
   if(rows.length||audits.length){if(rows.length!==1||audits.length!==1||JSON.stringify(rows[0])!==JSON.stringify(expectedRow)||JSON.stringify(audits[0])!==JSON.stringify(expectedAudit))return {ok:false,error:'CRF_PROJECTION_MISMATCH'};}
   else {if((t.V3_CrfState?.records||[]).some(r=>r.submission_id===record.submission_id))return {ok:false,error:'CRF_PROJECTION_MISSING'};after[n].push(expectedRow);after.CRFSubmissionAudit.push(expectedAudit);}
  }
  return {ok:true,after,result,audit_detail:{actor:u.id,action:a,at:deps.now(),registration_id:p.registration_id,reason:p.correction_reason||'',record_key:p.record_key,submission_id:p.submission_id||''}};
 }
 function plan(a,p,t,u,id){
  if(['reset_draft_code','update_draft_email','void_registration'].includes(a))return juogAdminPlanV3_(a,p,t,u,deps.adminRuntime(u,id));
  if(['save_crf','read_crf'].includes(a))return crfPlan(a,p,t,u);
  const q=clone(p);if(['radiology','medical_oncology','urology'].includes(u.role)){q.reviewer_role=u.role;q.reviewer_name=u.id;}if(u.role==='admin')q.admin_user=u.id;
  // Lists/stats run on a scoped copy, but may not replace the complete materialized view.
  const isList=['list_screenings','list_review_cases','stats','get_screening'].includes(a);
  let input=isList?scoped(t,u):t;
  if(a==='list_review_cases'){const h=input.Screening[0],si=h.indexOf('screening_id');input.Screening=[h,...input.Screening.slice(1).filter(r=>deps.assignments(u).includes(r[si]))];}
  const r=deps.legacyPlan(a,q,input);if(!r.ok)return r;
  if(isList)r.after=clone(t);
  if(a==='get_mdt_reviews'&&u.role!=='admin'){
   const v=r.result;r.result={ok:true,screening_id:v.screening_id,review_round:v.review_round,completed:v.completed,required:v.required,all_complete:v.all_complete,reviews:Object.fromEntries(['radiology','medical_oncology','urology'].map(role=>[role,v.reviews&&v.reviews[role]?{submitted:true}:null]))};
  }
  if(a==='save_draft'||a==='save_screening_draft'){r.after.V3_DraftOwners={...(t.V3_DraftOwners||{}),[draftKey(p)]:u.id};}
  // Keep ownership tombstones after view deletion; another user cannot claim a deleted key.
  r.result=deps.redact(r.result);
  r.audit_detail={actor:u.id,action:a,at:deps.now(),reason:p.correction_reason||p.reason||'',screening_id:p.screening_id||r.result.screening_id||'',registration_id:p.registration_id||r.result.registration_id||''};
  return r;
 }
 const service=new JuogDomainServiceV3({...deps,authorize,plan});
 const readActions=['list_review_cases','get_screening_crf','get_own_review','list_screenings','get_screening','get_mdt_reviews','stats','get_screening_draft','get_draft','get_crf_linkage','validate','read_crf'];
 function execute(assertion,operation){
  const op=clone(operation);if(op.payload&&typeof op.payload==='object'){if(typeof op.payload.registration_id==='string')op.payload.registration_id=juogNormalizeRegistrationV3_(op.payload.registration_id);if(typeof op.payload.reporter_email==='string')op.payload.reporter_email=juogPythonStripV3_(op.payload.reporter_email);}
  if(!readActions.includes(op.action))return service.execute(assertion,op);
  try{return deps.withLock(()=>{const u=deps.authenticate(assertion),v=service.readView(),permit=authorize(u,op.action,op.payload,v.tables);if(!permit.ok)return permit;const r=plan(op.action,op.payload,v.tables,u,op.id);if(!r.ok)return r;if(JSON.stringify(r.after)!==JSON.stringify(v.tables))return {ok:false,error:'READ_MUTATION_REJECTED'};return {ok:true,revision:v.revision,result:r.result,read_only:true};});}catch(_){return {ok:false,error:'READ_INCOMPLETE'};}
 }

 return {execute,authorize,readView:service.readView,routeNames:()=>[...facilityActions,...reviewerActions,...adminActions]};
}

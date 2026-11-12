const fs=require('fs'),crypto=require('crypto'),assert=require('assert/strict');const dir=__dirname;
const source=fs.readFileSync(dir+'/bundle/isolated_review_bundle.gs','utf8');
const headerCode=source.slice(source.indexOf('const REGISTRY_HEADERS ='),source.indexOf('function authorizeJuogAction_'));
const headers=new Function(headerCode+';return {Registry:REGISTRY_HEADERS,Screening:SCREENING_HEADERS,ScreeningAudit:SCREENING_AUDIT_HEADERS,MDTReviews:MDT_REVIEW_HEADERS,ScreeningCRF:CRF_BASE_HEADERS,CRF_30d:CRF_BASE_HEADERS,CRF_90d:CRF_BASE_HEADERS,CRF_Followup:CRF_BASE_HEADERS,CRFSubmissionAudit:CRF_AUDIT_HEADERS,CRF_Drafts:CRF_DRAFT_HEADERS};')();
const api=new Function(source+';return {Service:JuogUnifiedDomainV3,planner:juogLegacyPlanV3_,privacy:containsDirectIdentifier_,redact:stripDirectIdentifiers_,validate:validateClinicalV3};')();
const Service=api.Service,planner=api.planner;
class FakeDate extends Date{constructor(...a){super(...(a.length?a:['2026-11-11T02:00:00Z']));}}
const runtime={Date:FakeDate,draftPepper:'LOCAL_DUMMY_NO_REAL_SECRET',utilities:{getUuid:()=>crypto.randomUUID(),formatDate:(d,z,f)=>f==='yyyy-MM-dd'?d.toISOString().slice(0,10):d.toISOString(),DigestAlgorithm:{SHA_256:'sha256'},Charset:{UTF_8:'utf8'},computeDigest:(_,s)=>[...crypto.createHash('sha256').update(s).digest()],computeHmacSha256Signature:(s,k)=>[...crypto.createHmac('sha256',k).update(s).digest()],base64EncodeWebSafe:b=>Buffer.from(b).toString('base64url')}};
const baseline=Object.fromEntries(Object.entries(headers).map(([k,v])=>[k,[v]]));baseline.Settings=[['key','value']];const original=JSON.stringify(baseline);let db={baseline:structuredClone(baseline),intents:[],audits:[],commits:[]},fault=false,locked=false;
const users={facility:{id:'facility-1',enabled:true,role:'facility'},admin:{id:'admin-1',enabled:true,role:'admin'},radiology:{id:'rad-1',enabled:true,role:'radiology'},medical_oncology:{id:'onco-1',enabled:true,role:'medical_oncology'},urology:{id:'uro-1',enabled:true,role:'urology'}};
// The full per-case ACL adapter is independently tested; these fixtures are assigned explicitly.
const deps={authenticate:k=>users[k],authorize:(u,a,p)=>({ok:(a==='submit_screening'?u.role==='facility':a==='submit_mdt_review'?u.role===p.reviewer_role:a==='finalize_mdt'?u.role==='admin':true),error:'ROLE_NOT_ALLOWED'}),privacy:()=>false,hash:s=>crypto.createHash('sha256').update(s).digest('hex'),now:()=>new Date().toISOString(),withLock:f=>{if(locked)throw Error('LOCK');locked=true;try{return f()}finally{locked=false}},plan:(a,p,s,u)=>{if(a==='submit_mdt_review')p.reviewer_name=u.id;if(a==='finalize_mdt')p.admin_user=u.id;return planner(a,p,s,runtime)},store:{read:()=>structuredClone(db),assertFits:()=>{},appendIntent:i=>db.intents.push(i),appendAudit:a=>{if(fault)throw Error('fault');db.audits.push(a)},appendCommit:c=>db.commits.push(c)}};
for(const u of Object.values(users))u.facilities=['TEST01'];
Object.assign(deps,{privacy:api.privacy,redact:api.redact,validate:api.validate,today:()=> '2027-12-01',assignments:()=>['JUOG-SCR-001'],legacyPlan:(a,p,t)=>planner(a,p,t,runtime),adminRuntime:()=>({now:deps.now,privacy:api.privacy,resumeCode:()=> '123456',codeHash:s=>crypto.createHmac('sha256','LOCAL_ONLY').update(s).digest('hex'),voidPolicyApproved:true})});
const svc=new Service(deps),results=[];
users.second={...users.facility,id:'second-user'};
const fixture=JSON.parse(fs.readFileSync(dir+'/test01_e2e_steps.review.json','utf8'));
for(const step of fixture.steps){
 const before=JSON.stringify(db);
 const result=svc.execute(step.role,structuredClone(step.operation));
 assert.equal(result.ok,step.expected_ok,step.operation.id+':'+JSON.stringify(result));
 if(!step.expected_ok)assert.equal(JSON.stringify(db),before,'Rejected request changed journal');
 results.push({id:step.operation.id,action:step.operation.action,expected_ok:step.expected_ok,actual_ok:result.ok,error:result.error||null});
 if(step.operation.id==='op9'){
  const view=svc.readView().tables;
  assert.equal(view.CRF_30d.length,3);assert.equal(view.CRFSubmissionAudit.length,3);
  assert.deepEqual(view.V3_CrfState.records.map(r=>r.record_version),[1,2]);
  assert.equal(view.V3_CrfState.audits.length,2);
 }
 if(step.operation.id==='op30'){
  assert.equal(result.result.total,0);assert.equal(result.result.cN1,0);assert.equal(result.result.SD,0);
 }
}
assert.equal(JSON.stringify(db.baseline),original);
const report={scope:'OFFLINE ONLY; exact review bundle with TEST01 fixture; synthetic roles and in-memory journal; controlled business clocks. Not real IdP, GAS, Sheets or formal UAT.',bundle_sha256:crypto.createHash('sha256').update(source).digest('hex'),fixture_sha256:crypto.createHash('sha256').update(fs.readFileSync(dir+'/test01_e2e_steps.review.json')).digest('hex'),steps:results,baseline_unchanged:true,formal_pass_added:0};
fs.writeFileSync(dir+'/../uat_evidence/test01_workflow_replay_20261112.json',JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify({completed:results.length,rejected:results.filter(r=>!r.actual_ok).length,formal_pass_added:0}));

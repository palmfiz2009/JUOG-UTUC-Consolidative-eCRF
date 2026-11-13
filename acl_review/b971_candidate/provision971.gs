/* Editor-only: append one fictional Registry row, never impersonate OIDC. */
function juogProvisionFixture971Core_(d){
 const id='UAT_B971_FIXTURE_20261113',action='ISOLATED_FIXTURE_INITIALIZATION',actor={id:'PI_AUTHORIZED_FIXTURE_SETUP',enabled:true,role:'fixture_setup'};
 const expected={registered_at:'2026-04-01',registration_id:'JUOG-971',status:'ACTIVE',facility_code:'TEST01',facility_name:'完全架空施設',consent_date:'2026-03-25'};
 const payload={fixture_id:'JUOG-971',fixture_manifest_sha256:d.fixtureSha,approval_ref:'PI_B971_CONDITIONAL_EXECUTION_20261113'};
 d.guard();const before=d.store.read();
 const existing=before.intents.filter(i=>i.id===id);
 if(existing.length>1)throw Error('FIXTURE_CONFLICT');
 if(!existing.length&&JSON.stringify(before).includes('JUOG-971'))throw Error('FIXTURE_ALREADY_USED');
 const baseHash=d.hash(JSON.stringify(before.baseline));
 const svc=new JuogDomainServiceV3({authenticate:()=>actor,authorize:(u,a,p)=>({ok:u.id===actor.id&&a===action&&JSON.stringify(p)===JSON.stringify(payload),error:'FIXTURE_SCOPE_INVALID'}),privacy:()=>false,hash:d.hash,now:d.now,withLock:f=>f(),store:d.store,
  plan:(a,p,t)=>{
   d.guard();const after=JSON.parse(JSON.stringify(t)),h=after.Registry[0];
   if(new Set(h).size!==h.length||Object.keys(expected).some(k=>!h.includes(k))||JSON.stringify(t).includes('JUOG-971'))throw Error('FIXTURE_ALREADY_USED');
   after.Registry.push(h.map(k=>expected[k]||''));
   return {ok:true,after,result:{fixture_id:'JUOG-971',fictional:true},audit_detail:{scope:'EDITOR_ONLY_FICTIONAL_INITIALIZATION',approval_ref:payload.approval_ref,fixture_manifest_sha256:d.fixtureSha,synthetic_business_dates:true,actual_initialization_at:d.now(),no_clinical_submission_claim:true}};
  }});
 const previous=svc.readView();
 if(!existing.length&&previous.revision!==7)throw Error('FIXTURE_BASE_REVISION');
 const result=svc.execute('editor-fixed-setup',{id,action,payload,expected_revision:7});
 if(!result.ok)return result;
 const after=d.store.read(),view=svc.readView(),intent=after.intents.find(i=>i.id===id);
 if(view.revision!==8||intent.revision!==8||d.hash(JSON.stringify(after.baseline))!==baseHash)throw Error('FIXTURE_READBACK_MISMATCH');
 // Compare the complete pre-setup view, not merely the 970 Registry row.
 const prior=before.intents.filter(i=>i.revision===7&&before.commits.some(c=>c.id===i.id));
 if(prior.length!==1)throw Error('FIXTURE_PRIOR_VIEW');
 const stripped=JSON.parse(JSON.stringify(view.tables)),h=stripped.Registry[0],idx=h.indexOf('registration_id');
 const matches=stripped.Registry.slice(1).filter(r=>r[idx]==='JUOG-971');
 if(matches.length!==1||JSON.stringify(matches[0])!==JSON.stringify(h.map(k=>expected[k]||'')))throw Error('FIXTURE_ROW_MISMATCH');
 stripped.Registry=[h,...stripped.Registry.slice(1).filter(r=>r[idx]!=='JUOG-971')];
 if(JSON.stringify(stripped)!==JSON.stringify(prior[0].after))throw Error('FIXTURE_UNRELATED_CHANGE');
 for(const k of ['intents','audits','commits','requests','requestEvents']){
  const old=before[k].filter(r=>r.id!==id),now=after[k].filter(r=>r.id!==id);
  if(JSON.stringify(old)!==JSON.stringify(now))throw Error('FIXTURE_HISTORY_CHANGED');
 }
 return {ok:true,existing:result.existing===true,fixture_id:'JUOG-971',revision:8,prior_business_view_unchanged:true,setup_actor_not_oidc:true};
}

function juogB971Admin_(mode){
 const script='11wSp4ePaP5b5A2b5ITZZSZa3YTe-Ex-Tu6oGlEkkRfkPrMCA4deVSZDy',sheet='1Hd6EHDPZe8zGcDbILkaBLubgF5atfAzRfpPSN5LemiU';
 const prefixHash='8441de491fb974555aa0e63f4e690974c6c4af4f890493e1ed8af51b96609b24';
 const lock=LockService.getScriptLock();if(!lock.tryLock(30000)){console.info('B971_LOCK_REFUSED');return false;}
 let props,c,ss,writeAttempted=false;
 const hash=s=>Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256,s,Utilities.Charset.UTF_8).map(b=>('0'+((b+256)%256).toString(16)).slice(-2)).join('');
 function config(){
  if(ScriptApp.getScriptId()!==script||!lock.hasLock())throw Error('TARGET');
  const v=JSON.parse(props.getProperty('UNIFIED_ISOLATION_CONFIG')||'null');
  if(!v||v.environment!=='ISOLATED_TEST'||v.spreadsheetId!==sheet||v.approvedSpreadsheetId!==sheet||v.sessionPolicy!=='isolated_gas_session_b2'||v.sessionStoreGeneration!=='d72bcf33-423d-4c4d-862d-2e2d69bc3edf')throw Error('TARGET');
  return v;
 }
 function guard(){
  const v=config();
  if(v.sessionExecutionStage!=='AUTH_CONNECT'||v.notificationsDisabled!==true||v.backupVerified!==true||v.qaApproved!==true||v.fictionalBaselineVerified!==true||v.authConnectReviewApproved!==true||!v.authConnectReviewRef||!v.approvalRef)throw Error('GATES');
  const rows=ss.getSheetByName('D3_Journal').getDataRange().getValues();
  if(hash(JSON.stringify(rows.slice(0,66)))!==prefixHash)throw Error('PREFIX_CHANGED');
  if(hash(JSON.stringify(ss.getSheetByName('UAT971_BACKUP_20261113').getDataRange().getValues()))!==prefixHash)throw Error('BACKUP');
  const acl=ss.getSheetByName('V3_Users').getDataRange().getValues();
  if(acl.length!==2||JSON.stringify(acl[0])!==JSON.stringify(['issuer','subject','user_id','enabled','role','facility_ids_json','valid_until'])||acl[1][2]!=='UAT_TEST01_PI_01'||acl[1][3]!==true||acl[1][4]!=='facility'||acl[1][5]!=='["TEST01"]'||acl[1][6]!=='2026-11-19T23:59:00+09:00'||Date.now()>=new Date(acl[1][6]).getTime())throw Error('ACL');
  if(hash(JSON.stringify(['JUOG-ACL-PROPOSAL-v1',String(acl[1][0]),String(acl[1][1])]))!=='f0ea0ddb132e96bbd08cba4e37dc38609b73db5740530a05225c5acb6cab798f')throw Error('ACL');
 }
 try{
  props=PropertiesService.getScriptProperties();c=config();
  if(mode==='disable'){
   c.sessionExecutionStage='AUTH_CONNECT';c.auth04ScopeReviewed=false;c.auth04ExecutionApprovalRef=null;c.b971ExecutionUntil=0;
  }else{
   ss=SpreadsheetApp.openById(sheet);guard();
   const store=juogDomainSheetsStoreV3_(ss,hash,()=>Utilities.getUuid(),guard);
   if(mode==='check'){
    const data=store.read();const svc=new JuogDomainServiceV3({store,hash});const view=svc.readView();
    console.info(JSON.stringify({ok:true,stage:'AUTH_CONNECT',journal_rows:ss.getSheetByName('D3_Journal').getLastRow(),revision:view.revision,fixture971_used:JSON.stringify(data).includes('JUOG-971'),backup_verified:true,acl_count:1,role:'facility',configuration_changed:false}));return true;
   }
   if(mode==='provision'){
    const r=juogProvisionFixture971Core_({guard,hash,now:()=>new Date().toISOString(),fixtureSha:B971_FIXTURE_SHA,store});
    console.info(JSON.stringify({ok:r.ok===true,fixture_id:'JUOG-971',revision:r.ok?r.revision:null,prior_business_view_unchanged:r.prior_business_view_unchanged===true,error:r.ok?null:'B971_PROVISION_INCOMPLETE'}));return r.ok===true;
   }
   if(mode!=='enable')throw Error('MODE');
   const svc=new JuogDomainServiceV3({store,hash}),v=svc.readView();
   if(v.revision!==8||v.tables.Registry.length!==3||!store.read().intents.some(i=>i.id==='UAT_B971_FIXTURE_20261113'&&i.audit_detail.fixture_manifest_sha256===B971_FIXTURE_SHA))throw Error('FIXTURE');
   c.sessionExecutionStage='AUTH04_APPROVED';c.auth04ScopeReviewed=true;c.auth04ScopeReviewRef='B971_INDEPENDENT_REVIEW_20261113';c.auth04FixtureProvisioned=true;c.auth04FixtureManifestSha256=B971_FIXTURE_SHA;c.auth04ExecutionApprovalRef='PI_B971_CONDITIONAL_EXECUTION_20261113';c.b971ExecutionUntil=Date.now()+60*60*1000;
  }
  const value=JSON.stringify(c);writeAttempted=true;props.setProperty('UNIFIED_ISOLATION_CONFIG',value);if(props.getProperty('UNIFIED_ISOLATION_CONFIG')!==value)throw Error('READBACK');
  console.info(JSON.stringify({ok:true,stage:c.sessionExecutionStage,scope:'TEST01/JUOG-971',business_enabled:mode==='enable'}));return true;
 }catch(_){
  if(writeAttempted&&props&&c){try{c.sessionExecutionStage='AUTH_CONNECT';c.auth04ScopeReviewed=false;c.auth04ExecutionApprovalRef=null;c.b971ExecutionUntil=0;props.setProperty('UNIFIED_ISOLATION_CONFIG',JSON.stringify(c));if(props.getProperty('UNIFIED_ISOLATION_CONFIG')!==JSON.stringify(c))throw Error('READBACK');console.info('B971_FAILED_AUTH_CONNECT_VERIFIED');return false;}catch(_){console.info('B971_CONFIG_UNKNOWN_STOP');return false;}}
  console.info('B971_REFUSED_NO_CONFIG_CHANGE');return false;
 }finally{lock.releaseLock();}
}
function juogB971Readiness(){return juogB971Admin_('check');}
function juogB971Provision(){return juogB971Admin_('provision');}
function juogB971Enable(){return juogB971Admin_('enable');}
function juogB971Disable(){return juogB971Admin_('disable');}

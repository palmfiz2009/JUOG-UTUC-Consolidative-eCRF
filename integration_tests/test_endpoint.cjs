/* Full PR15 GAS + actual auth/session verifier. Google services are in-memory;
 * all values fictional. No network, no credentials, no external writes. */
const fs=require('fs'),vm=require('vm'),crypto=require('crypto'),assert=require('assert/strict'),path=require('path');
const root=path.resolve(__dirname,'..');
const hash=s=>crypto.createHash('sha256').update(s).digest('hex');
const copy=x=>JSON.parse(JSON.stringify(x));
const files=['05_registry_google_apps_script.gs','isolated_auth_bridge.gs','isolated_session_store.gs','isolated_crf_endpoint.gs'];
function fixture(){
 let now=Date.parse('2026-11-16T00:00:00Z'),locked=false,drop='',expireOn='',nextJti=0;
 const props={},tables={};
 class Sheet{
  constructor(name,rows){this.name=name;this.rows=copy(rows);}
  getDataRange(){return {getValues:()=>copy(this.rows.map(r=>Array.from({length:this.getLastColumn()},(_,i)=>r[i]??'')))}};
  getLastColumn(){return Math.max(0,...this.rows.map(r=>r.length))}
  getLastRow(){return this.rows.length}
  getRange(r,c,n=1,m=1){return {getValues:()=>Array.from({length:n},(_,i)=>Array.from({length:m},(_,j)=>this.rows[r-1+i]?.[c-1+j]??'')),setValues:values=>{values.forEach((line,i)=>line.forEach((v,j)=>{this.rows[r-1+i]??=[];this.rows[r-1+i][c-1+j]=v;}));},setValue:v=>{this.rows[r-1]??=[];this.rows[r-1][c-1]=v;}}}
  appendRow(r){if(drop!==this.name)this.rows.push(copy(r));if(expireOn===this.name)now+=16000;}
  deleteRow(n){if(drop!==this.name)this.rows.splice(n-1,1)}
  setFrozenRows(){}
 }
 const ss={getId:()=>c.spreadsheetId,getName:()=> 'TEST_OFFLINE',getSheetByName:n=>tables[n]||null,insertSheet:()=>{throw Error('UNEXPECTED_CREATION')}};
 const x={Date:class extends Date{constructor(...a){super(...(a.length?a:[now]))}static now(){return now}},
  ScriptApp:{getScriptId:()=>c.scriptId},
  PropertiesService:{getScriptProperties:()=>({getProperty:k=>props[k]??null,setProperty:(k,v)=>props[k]=v})},
  LockService:{getScriptLock:()=>({tryLock:()=>{if(locked)return false;locked=true;return true},releaseLock:()=>locked=false})},
  SpreadsheetApp:{openById:id=>{assert.equal(id,c.spreadsheetId);return ss},flush:()=>{}},
  Utilities:{DigestAlgorithm:{SHA_256:'sha256'},Charset:{UTF_8:'utf8'},computeDigest:(_,s)=>[...crypto.createHash('sha256').update(s).digest()],computeHmacSha256Signature:(s,k)=>[...crypto.createHmac('sha256',k).update(s).digest()],base64DecodeWebSafe:s=>[...Buffer.from(s,'base64url')],base64EncodeWebSafe:b=>Buffer.from(b).toString('base64url'),newBlob:b=>({getDataAsString:()=>Buffer.from(b).toString()}),getUuid:()=>crypto.randomUUID(),formatDate:d=>new Date(d).toISOString()},
  console};
 const c={enabled:true,stage:'PR15_ISOLATED_CRFS',scriptId:'1_oVuL1i6Kmyu5egp-iDHIku-nN5JxoQ1ySPSluAsNc2gCFXGvBSJGDAR',spreadsheetId:'1XaLdVGN39skmXVhiyPN-uOb9B8zjo3rmbNgYZCndJRs',notificationsDisabled:true,sessionPolicy:'isolated_gas_session_b2',sessionStoreApproved:true,sessionStoreGeneration:'OFFLINE_ONLY',bridgeIssuer:'JUOG_PR15_FIXTURE',audience:'JUOG_PR15_GAS',oidcIssuer:'https://accounts.google.com',signingKey:'fictional-offline-key-not-a-credential',qaRef:'OFFLINE_TEST_NOT_APPROVAL',piRef:'OFFLINE_TEST_NOT_APPROVAL',singleWriterRef:'OFFLINE_TEST_NOT_APPROVAL',backupRef:'OFFLINE_TEST_NOT_APPROVAL',b2PolicyRef:'OFFLINE_TEST_NOT_APPROVAL'};
 vm.createContext(x);for(const f of files)vm.runInContext(fs.readFileSync(path.join(root,f),'utf8'),x,{filename:f});
 const add=(name,rows)=>tables[name]=new Sheet(name,rows);
 for(const [name,headers] of [['Registry','REGISTRY_HEADERS'],['CRF_30d','CRF_BASE_HEADERS'],['CRF_90d','CRF_BASE_HEADERS'],['CRF_Followup','CRF_BASE_HEADERS'],['CRFSubmissionAudit','CRF_AUDIT_HEADERS'],['CRF_Drafts','CRF_DRAFT_HEADERS']])add(name,[vm.runInContext(headers,x)]);
 const row=(name,obj)=>tables[name].appendRow(tables[name].rows[0].map(k=>obj[k]??''));
 row('Registry',{registration_id:'JUOG-901',facility_code:'TEST01',facility_name:'FICTIONAL',status:'ACTIVE',registered_at:'2026-01-01',consent_date:'2026-01-01'});
 add('V3_Users',[['issuer','subject','user_id','enabled','role','facility_ids_json','valid_until'],[c.oidcIssuer,'fictional-sub','fictional-user',true,'facility','["TEST01"]','2026-12-01']]);
 add('V3_SessionEvents',[['sequence','event_json','chain_sha256']]);
 add('R1_CaseOwners',[['registration_id','facility_code','user_id','enabled'],['JUOG-901','TEST01','fictional-user',true]]);
 add('R1_Operations',[['sequence','event_json','digest']]);add('R1_DraftOwners',[['draft_key','user_id']]);add('R1_DraftEvents',[['event_json','digest']]);
 props.SPREADSHEET_ID=c.spreadsheetId;props['JUOG_B2_HEAD_'+c.spreadsheetId]='0:'+hash('JUOG-B2|'+c.spreadsheetId+'|'+c.sessionStoreGeneration);
 const origin=Math.floor(now/1000);
 function envelope(action,payload,changes={}){
  const request_json=JSON.stringify({action,payload}),time=Math.floor(now/1000);
  const claims={v:2,iss:c.bridgeIssuer,aud:c.audience,oidc_issuer:c.oidcIssuer,sub:'fictional-sub',iat:time,exp:Math.min(time+15,origin+3600),request_hash:hash(request_json),session:{sid:hash('offline-session'),jti:hash(String(++nextJti)).slice(0,32),generation:c.sessionStoreGeneration,token_iat:origin,deadline:origin+3600},...changes};
  const data=Buffer.from(JSON.stringify(claims)).toString('base64url');
  return {request_json,identity_assertion:data+'.'+crypto.createHmac('sha256',c.signingKey).update(data).digest('base64url')};
 }
 const call=(a,p={})=>copy(x.juogPr15Entry_(envelope(a,p),c));
 const payload=(type='perioperative_30d',visit='30d',uuid='offline-v1')=>({registration_id:'JUOG-901',facility_code:'TEST01',facility_name:'FICTIONAL',reporter_email:'fictional@example.invalid',crf_type:type,visit,record_key:['JUOG-901',type,visit].join('|'),submission_id:uuid,submission_kind:'初回報告',data:{surgery_performed:'実施した',operation_date:'2026-01-10',reference_date:'2026-01-10',source_30d_linked:true,source_30d_record_version:1,source_30d_submission_id:'offline-v1'}});
 const save=(p,expected=0)=>call('save_crf',{payload:p,expected_record_version:expected});
 return {x,c,tables,props,call,save,payload,envelope,row,drop:n=>drop=n,expireOn:n=>expireOn=n,advance:ms=>now+=ms,lock:v=>locked=v};
}
const tests=[];function test(name,fn){const f=fixture();fn(f);tests.push(name);console.log('PASS '+name)}
test('default disabled, wrong script/workbook and old generation deny',f=>{for(const [k,v] of [['enabled',false],['scriptId','other'],['spreadsheetId','other'],['qaRef',''],['sessionStoreGeneration','d72bcf33-423d-4c4d-862d-2e2d69bc3edf']]){const old=f.c[k];f.c[k]=v;assert.equal(f.call('backend_info').error,'INTEGRATION_NOT_APPROVED');f.c[k]=old;}});
test('no legacy token bypass, bad signature and payload tamper',f=>{assert.equal(f.x.juogPr15Entry_({token:'legacy',action:'save_crf'},f.c).error,'AUTH_REQUIRED');let e=f.envelope('backend_info',{});e.identity_assertion+='x';assert.equal(f.x.juogPr15Entry_(e,f.c).error,'AUTH_INVALID');e=f.envelope('backend_info',{});e.request_json+=' ';assert.equal(f.x.juogPr15Entry_(e,f.c).error,'REQUEST_SIGNATURE_MISMATCH');});
test('valid native-derived signed context and assert replay',f=>{const e=f.envelope('ui_context',{});assert.equal(f.x.juogPr15Entry_(e,f.c).ok,true);assert.equal(f.x.juogPr15Entry_(e,f.c).error,'ASSERTION_REPLAY');});
test('ACL disabled expired wrong role other facility and duplicate principal',f=>{const r=f.tables.V3_Users.rows[1];for(const [i,v] of [[3,false],[4,'admin'],[4,'INVALID'],[5,'["OTHER"]'],[6,'2000-01-01']]){const old=r[i];r[i]=v;assert.equal(f.call('ui_context').ok,false);r[i]=old;}f.tables.V3_Users.rows.push(copy(r));assert.equal(f.call('ui_context').ok,false);assert.equal(f.tables.CRF_30d.rows.length,1);});
test('signature expiry and 60min deadline nonrenewal',f=>{const e=f.envelope('ui_context',{});f.advance(15000);assert.equal(f.x.juogPr15Entry_(e,f.c).error,'AUTH_EXPIRED');f.advance(3585000);assert.equal(f.call('ui_context').ok,false);});
test('logout rejects pending signature and future requests',f=>{const e=f.envelope('ui_context',{});assert.equal(f.call('session_revoke').revoked,true);assert.equal(f.x.juogPr15Entry_(e,f.c).error,'SESSION_REVOKED');assert.equal(f.call('ui_context').error,'SESSION_REVOKED');});
test('case ownership, facility injection and forbidden routes deny',f=>{const p=f.payload();p.facility_code='OTHER';assert.equal(f.save(p).error,'SUBJECT_FORBIDDEN');p.facility_code='TEST01';p.role='admin';assert.equal(f.save(p).error,'ACTOR_OVERRIDE_DENIED');f.tables.R1_CaseOwners.rows[1][2]='other';assert.equal(f.call('validate',{registration_id:'JUOG-901'}).error,'SUBJECT_FORBIDDEN');assert.equal(f.call('register',{}).error,'ROUTE_DENIED');});
test('all nine visits v1 v2 immutable replay audit and actor',f=>{
 for(const [type,visits] of [['perioperative_30d',['30d']],['day90',['90d']],['followup',['6m','9m','12m','15m','18m','21m','24m']]])for(const visit of visits){
  let p=f.payload(type,visit,type==='perioperative_30d'?'offline-v1':'offline-'+visit);if(type!=='perioperative_30d'){p.data.source_30d_record_version=2;p.data.source_30d_submission_id='offline-v1-v2';}
  let r=f.save(p);assert.equal(r.ok,true,JSON.stringify(r));assert.equal(r.record_version,1);
  const initial=copy(f.tables[type==='perioperative_30d'?'CRF_30d':type==='day90'?'CRF_90d':'CRF_Followup'].rows[1]);
  assert.equal(f.save(p).existing,true);let q=copy(p);q.submission_kind='訂正報告';q.correction_reason='FICTIONAL';q.submission_id+='-v2';q.data.note='corrected';r=f.save(q,1);assert.equal(r.ok,true,JSON.stringify(r));assert.equal(r.record_version,2);assert.equal(f.save(q,1).existing,true);
  assert.deepEqual(f.tables[type==='perioperative_30d'?'CRF_30d':type==='day90'?'CRF_90d':'CRF_Followup'].rows[1],initial);
 }
 assert.equal(f.tables.CRFSubmissionAudit.rows.length,19);const events=f.tables.R1_Operations.rows.slice(1).map(r=>JSON.parse(r[1]));assert.equal(events.filter(e=>e.kind==='COMMIT').length,18);assert(events.every(e=>e.actor==='fictional-user'));
});
test('same UUID different content rejected and version conflict',f=>{const p=f.payload();assert.equal(f.save(p).ok,true);const mutated=copy(p);mutated.data.note='different';assert.equal(f.save(mutated).error,'SUBMISSION_ID_CONFLICT');const correction=copy(p);correction.submission_kind='訂正報告';correction.correction_reason='FICTIONAL';correction.submission_id='c1';assert.equal(f.save(correction,1).ok,true);correction.submission_id='c2';assert.equal(f.save(correction,1).error,'VERSION_CONFLICT');assert.equal(f.tables.CRF_30d.rows.length,3);});
test('single writer lock contention fails before storage',f=>{f.lock(true);assert.equal(f.save(f.payload()).error,'LOCK_TIMEOUT');assert.equal(f.tables.R1_Operations.rows.length,1);});
test('lost audit append blocks success then same UUID repairs',f=>{const p=f.payload();f.drop('CRFSubmissionAudit');assert.equal(f.save(p).ok,false);assert.equal(f.tables.CRF_30d.rows.length,2);const other=copy(p);other.submission_id='other';assert.equal(f.save(other).error,'PENDING_OPERATION');f.drop('');assert.equal(f.save(p).ok,true);assert.equal(f.tables.CRF_30d.rows.length,2);assert.equal(f.tables.CRFSubmissionAudit.rows.length,2);});
test('silent CRF append and operation append never success',f=>{const p=f.payload();f.drop('R1_Operations');assert.equal(f.save(p).ok,false);assert.equal(f.tables.CRF_30d.rows.length,1);f.drop('CRF_30d');assert.equal(f.save(p).ok,false);f.drop('');assert.equal(f.save(p).ok,true);assert.equal(f.tables.CRF_30d.rows.length,2);});
test('expiry between body and audit no successful receipt',f=>{f.expireOn('CRF_30d');assert.equal(f.save(f.payload()).ok,false);assert.equal(f.tables.CRFSubmissionAudit.rows.length,1);f.expireOn('');assert.equal(f.save(f.payload()).ok,true);assert.equal(f.tables.CRF_30d.rows.length,2);});
test('corrupt session head closes gate',f=>{f.props['JUOG_B2_HEAD_'+f.c.spreadsheetId]='corrupt';assert.equal(f.save(f.payload()).error,'SESSION_STORE_INVALID');assert.equal(f.tables.CRF_30d.rows.length,1);});
test('committed missing CRF is not recreated as success',f=>{const p=f.payload();assert.equal(f.save(p).ok,true);f.tables.CRF_30d.rows.pop();assert.equal(f.save(p).error,'COMMITTED_RECORD_MISSING');});
test('draft save resume delete plus principal binding',f=>{const p={registration_id:'JUOG-901',facility_code:'TEST01',crf_type:'perioperative_30d',visit:'30d',reporter_email:'fictional@example.invalid',draft_state:{zero:0,flag:false}};assert.equal(f.call('save_draft',p).ok,true);assert.deepEqual(f.call('get_draft',p).draft_state,p.draft_state);f.tables.R1_DraftOwners.rows[1][1]='another';assert.equal(f.call('delete_draft',p).error,'SUBJECT_FORBIDDEN');f.tables.R1_DraftOwners.rows[1][1]='fictional-user';assert.equal(f.call('delete_draft',p).ok,true);assert.equal(f.call('get_draft',p).source_found,false);assert.equal(f.tables.R1_DraftEvents.rows.length,3);});
test('direct identifier and empty clinical payload rejected',f=>{let p=f.payload();p.data.patient_name='FICTIONAL';assert.equal(f.save(p).error,'DIRECT_IDENTIFIER_NOT_ALLOWED');p.data={};assert.equal(f.save(p).error,'PAYLOAD_INVALID');assert.equal(f.tables.CRF_30d.rows.length,1);});
test('read status is owner scoped and never asserts unverified success',f=>{const p=f.payload();assert.equal(f.save(p).ok,true);assert.equal(f.call('request_status',{registration_id:'JUOG-901',submission_id:p.submission_id}).state,'COMMITTED_RECHECK_REQUIRED');f.tables.R1_CaseOwners.rows[1][2]='OTHER';assert.equal(f.call('request_status',{registration_id:'JUOG-901',submission_id:p.submission_id}).error,'SUBJECT_FORBIDDEN');});
test('privacy regression encoded JSON NFKC camelcase free text',f=>{for(const data of [{regBirthDate:'1980-01-02'},{nested:'{"ＭＲＮ":"FICTIONAL"}'},{text:'生年月日1980年1月2日'}]){const p=f.payload();p.data=data;assert.equal(f.save(p).error,'DIRECT_IDENTIFIER_NOT_ALLOWED');}assert.equal(f.tables.CRF_30d.rows.length,1);});
test('missing schema and UUID/audit corruption fail closed',f=>{const p=f.payload();assert.equal(f.save(p).ok,true);f.tables.CRFSubmissionAudit.rows.push(copy(f.tables.CRFSubmissionAudit.rows[1]));assert.equal(f.save(p).ok,false);delete f.tables.R1_CaseOwners;assert.equal(f.call('validate',{registration_id:'JUOG-901'}).error,'SCHEMA_MISSING');});
test('actual fixture Python signer accepted by actual GAS verifier',f=>{
 const script=`import json,time
from types import SimpleNamespace
from unittest.mock import patch
from uat_b2_auth_bridge import signed_request
class User(dict):is_logged_in=True
u=User(iss='https://accounts.google.com',sub='fictional-sub',aud='offline-client',iat=1794787200,exp=1794794400,nonce='offline-nonce')
c=dict(oidc_issuer=u['iss'],oidc_client_id=u['aud'],signing_key='fictional-offline-key-not-a-credential',bridge_issuer='JUOG_PR15_FIXTURE',audience='JUOG_PR15_GAS',session_policy='isolated_gas_session_b2',session_environment='JUOG_AUTH04_ISOLATED_TEST01',session_store_generation='OFFLINE_ONLY',session_b_safety_review_approved=True,session_b_limited_execution_approved=True)
with patch('time.time',return_value=1794787200):print(json.dumps(signed_request(SimpleNamespace(user=u,secrets={'juog_identity_bridge':c}),'ui_context',{})))
`;
 const envelope=JSON.parse(require('child_process').execFileSync(process.env.PR15_PYTHON||'python',['-c',script],{cwd:root,encoding:'utf8'}));
 const result=f.x.juogPr15Entry_(envelope,f.c);assert.equal(result.ok,true,JSON.stringify(result));
});
fs.writeFileSync(path.join(root,'integration_evidence/endpoint_results.json'),JSON.stringify({mode:'OFFLINE_IN_MEMORY_REAL_SOURCE',test_groups:tests.length,tests,formal_uat_pass_delta:0,independent_qa_approved:false},null,2)+'\n');
console.log('ALL '+tests.length+' GROUPS PASSED');

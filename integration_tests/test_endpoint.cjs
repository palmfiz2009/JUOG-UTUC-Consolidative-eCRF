/* Full PR15 GAS + actual auth/session verifier. Google services are in-memory;
 * all values fictional. No network, no credentials, no external writes. */
const fs=require('fs'),vm=require('vm'),crypto=require('crypto'),assert=require('assert/strict'),path=require('path');
const root=path.resolve(__dirname,'..');
const hash=s=>crypto.createHash('sha256').update(s).digest('hex');
const copy=x=>JSON.parse(JSON.stringify(x));
const files=['05_registry_google_apps_script.gs','isolated_auth_bridge.gs','isolated_session_store.gs','isolated_crf_endpoint.gs','isolated_recovery.gs','clinical_contract_generated.gs','clinical_validation.gs','autosave_sections_generated.gs','isolated_autosave.gs'];
function fixture(){
 let now=Date.parse('2026-11-16T00:00:00Z'),locked=false,drop='',expireOn='',nextJti=0;
 const props={},tables={},metrics={opens:0,reads:{},lookups:{}};
 class Sheet{
  constructor(name,rows){this.name=name;this.rows=copy(rows);}
  getDataRange(){metrics.reads[this.name]=(metrics.reads[this.name]||0)+1;return {getValues:()=>copy(this.rows.map(r=>Array.from({length:this.getLastColumn()},(_,i)=>r[i]??'')))}};
  getLastColumn(){return Math.max(0,...this.rows.map(r=>r.length))}
  getLastRow(){return this.rows.length}
  getRange(r,c,n=1,m=1){return {getValues:()=>Array.from({length:n},(_,i)=>Array.from({length:m},(_,j)=>this.rows[r-1+i]?.[c-1+j]??'')),setValues:values=>{values.forEach((line,i)=>line.forEach((v,j)=>{this.rows[r-1+i]??=[];this.rows[r-1+i][c-1+j]=v;}));},setValue:v=>{this.rows[r-1]??=[];this.rows[r-1][c-1]=v;}}}
  appendRow(r){if(drop!==this.name)this.rows.push(copy(r));if(expireOn===this.name)now+=16000;}
  deleteRow(n){if(drop!==this.name)this.rows.splice(n-1,1)}
  setFrozenRows(){}
 }
 const ss={getId:()=>c.spreadsheetId,getName:()=> 'TEST_OFFLINE',getSheetByName:n=>{metrics.lookups[n]=(metrics.lookups[n]||0)+1;return tables[n]||null},insertSheet:()=>{throw Error('UNEXPECTED_CREATION')}};
 const x={Date:class extends Date{constructor(...a){super(...(a.length?a:[now]))}static now(){return now}},
  ScriptApp:{getScriptId:()=>c.scriptId},
  PropertiesService:{getScriptProperties:()=>({getProperty:k=>props[k]??null,setProperty:(k,v)=>props[k]=v})},
  LockService:{getScriptLock:()=>({tryLock:()=>{if(locked)return false;locked=true;return true},releaseLock:()=>locked=false})},
  SpreadsheetApp:{openById:id=>{metrics.opens++;assert.equal(id,c.spreadsheetId);return ss},flush:()=>{}},
  Utilities:{DigestAlgorithm:{SHA_256:'sha256'},Charset:{UTF_8:'utf8'},computeDigest:(_,s)=>[...crypto.createHash('sha256').update(s).digest()],computeHmacSha256Signature:(s,k)=>[...crypto.createHmac('sha256',k).update(s).digest()],base64DecodeWebSafe:s=>[...Buffer.from(s,'base64url')],base64EncodeWebSafe:b=>Buffer.from(b).toString('base64url'),newBlob:b=>({getDataAsString:()=>Buffer.from(b).toString()}),getUuid:()=>crypto.randomUUID(),formatDate:(d,tz,format)=>format==='yyyy-MM-dd'?new Date(d).toISOString().slice(0,10):new Date(d).toISOString()},
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
 const clinicalFixtures=JSON.parse(fs.readFileSync(path.join(root,'clinical_contract/valid_fixtures.json'),'utf8'));
 const payload=(type='perioperative_30d',visit='30d',uuid='offline-v1')=>{const p=copy(clinicalFixtures[type]);p.visit=visit;if(type==='followup')p.data.visit_month=visit.replace('m','ヶ月')+(visit==='24m'?'（終了）':'');p.record_key=['JUOG-901',type,visit].join('|');p.submission_id=uuid;return p;};

 const save=(p,expected=0)=>call('save_crf',{payload:p,expected_record_version:expected});
 return {x,c,tables,props,metrics,call,save,payload,envelope,row,drop:n=>drop=n,expireOn:n=>expireOn=n,advance:ms=>now+=ms,lock:v=>locked=v};
}
const tests=[];function test(name,fn){const f=fixture();fn(f);tests.push(name);console.log('PASS '+name)}
test('request-local sheet handles retain fresh cells and miss checks',f=>{
 let lookups=0;const raw={getId:()=> 'fixture',getName:()=> 'fixture',getSheetByName:n=>{lookups++;return f.tables[n]||null}};
 const ss=f.x.pr15WorkbookHandles_(raw),a=ss.getSheetByName('V3_Users');
 assert.equal(ss.getSheetByName('V3_Users'),a);assert.equal(lookups,1);
 a.rows[1][3]=false;
 assert.equal(ss.getSheetByName('V3_Users').getDataRange().getValues()[1][3],false);
 assert.equal(ss.getSheetByName('missing'),null);assert.equal(ss.getSheetByName('missing'),null);
 assert.equal(lookups,3);
 const next=f.x.pr15WorkbookHandles_(raw);next.getSheetByName('V3_Users');assert.equal(lookups,4);
});
test('full save resolves each sheet once but authorization reads stay live',f=>{
 const baseline=fixture();baseline.x.pr15WorkbookHandles_=raw=>raw;
 assert.equal(baseline.save(baseline.payload()).ok,true);
 assert.equal(f.save(f.payload()).ok,true);
 assert.ok(Object.values(f.metrics.lookups).every(n=>n===1));
 assert.deepEqual(f.metrics.reads,baseline.metrics.reads);
 const count=m=>Object.values(m.lookups).reduce((a,b)=>a+b,0);
 assert.ok(count(f.metrics)<count(baseline.metrics));
 console.log('HANDLE_LOOKUPS '+JSON.stringify({before:count(baseline.metrics),after:count(f.metrics),reads:f.metrics.reads}));
});
test('header no-op is read-only; changed headers and append recheck after reads',f=>{
 const sh=f.tables.CRF_30d,original=copy(sh.rows);
 vm.runInContext('JUOG_PR15_GUARD_=()=>{throw Error("SESSION_REVOKED")}',f.x);
 f.x.ensureDynamicHeaders_(sh,original[0]);
 assert.deepEqual(sh.rows,original);
 assert.throws(()=>f.x.ensureDynamicHeaders_(sh,['new_column']),/SESSION_REVOKED/);
 assert.deepEqual(sh.rows,original);
 let revoked=false;
 const getRange=sh.getRange.bind(sh);
 sh.getRange=(...args)=>{const r=getRange(...args);return {...r,getValues:()=>{const v=r.getValues();revoked=true;return v}}};
 f.x.guardAfterHeaderRead=()=>{if(revoked)throw Error('SESSION_REVOKED')};
 vm.runInContext('JUOG_PR15_GUARD_=guardAfterHeaderRead',f.x);
 assert.throws(()=>f.x.appendByHeaders_(sh,{submission_id:'fictional-blocked'}),/SESSION_REVOKED/);
 assert.deepEqual(sh.rows,original);
});
test('locked request opens workbook once without retaining handle',f=>{
 assert.equal(f.save(f.payload()).ok,true);assert.equal(f.metrics.opens,1);
 assert.equal(vm.runInContext('JUOG_PR15_WORKBOOK_',f.x),null);
 assert.equal(f.save(f.payload()).existing,true);assert.equal(f.metrics.opens,2);
});
test('workbook handle cleared after rejection and configured ID rechecked',f=>{
 const p=f.payload();p.data={};assert.equal(f.save(p).ok,false);
 assert.equal(vm.runInContext('JUOG_PR15_WORKBOOK_',f.x),null);
 vm.runInContext('JUOG_PR15_WORKBOOK_={id:"DIFFERENT",ss:{}}',f.x);
 assert.throws(()=>f.x.getSpreadsheet_(),/CONFIG_BINDING_MISMATCH/);
 vm.runInContext('JUOG_PR15_WORKBOOK_=null',f.x);
 assert.equal(f.save(f.payload()).ok,true);
});
test('journal append uses two fresh reads and both guards',f=>{
 const ss=f.x.getSpreadsheet_();let guards=0;
 const j=f.x.pr15Journal_(ss,()=>guards++),before=f.metrics.reads.R1_Operations||0;
 j.append({kind:'INTENT',uuid:'offline-journal',key:'key',actor:'fictional-user',digest:'digest'});
 assert.equal(f.metrics.reads.R1_Operations-before,2);assert.equal(guards,2);
 f.tables.R1_Operations.rows[1][2]='corrupt';
 assert.throws(()=>j.append({kind:'COMMIT',uuid:'offline-journal',key:'key',actor:'fictional-user',digest:'digest'}),/OPERATION_STORE_INVALID/);
 assert.equal(f.tables.R1_Operations.rows.length,2);
});
test('live-shaped expiry after audit requires same UUID recovery and keeps Version 1',f=>{
 const p=f.payload(),q={registration_id:p.registration_id,facility_code:p.facility_code,crf_type:p.crf_type,visit:p.visit};
 f.expireOn('CRFSubmissionAudit');assert.equal(f.save(p).error,'AUTH_EXPIRED');
 assert.equal(f.tables.CRF_30d.rows.length,2);assert.equal(f.tables.CRFSubmissionAudit.rows.length,2);
 assert.equal(f.tables.R1_Operations.rows.length,2);
 const original=copy(f.tables.CRF_30d.rows);
 f.expireOn('');assert.equal(f.call('recovery_status',q).recovery.state,'RETRY_ALLOWED');
 const r=f.call('recovery_retry',{...q,submission_id:p.submission_id});
 assert.equal(r.ok,true);assert.equal(r.record_version,1);assert.equal(r.existing,true);
 assert.deepEqual(f.tables.CRF_30d.rows,original);assert.equal(f.tables.CRFSubmissionAudit.rows.length,2);
 assert.equal(f.tables.R1_Operations.rows.length,3);
});
test('B2 request-local hash reuse still reads live cells and head',f=>{
 f.call('ui_context');
 const store=f.x.juogSessionStoreB2_(f.x.getSpreadsheet_(),f.c);
 let hashes=0;const digest=f.x.Utilities.computeDigest;
 f.x.Utilities.computeDigest=(...args)=>{hashes++;return digest(...args)};
 store.read();const first=hashes,reads=f.metrics.reads.V3_SessionEvents;
 store.read();assert.equal(hashes,first);assert.equal(f.metrics.reads.V3_SessionEvents,reads+1);
 f.props['JUOG_B2_HEAD_'+f.c.spreadsheetId]='corrupt';
 assert.throws(()=>store.read(),/SESSION_STORE_INVALID/);
});
test('B2 prefix reuse rejects old row tamper and truncation',f=>{
 f.call('ui_context');const sh=f.tables.V3_SessionEvents,store=f.x.juogSessionStoreB2_(f.x.getSpreadsheet_(),f.c);
 store.read();const old=sh.rows[1][1];sh.rows[1][1]=old.replace('OPEN','REVOKE');
 assert.throws(()=>store.read(),/SESSION_STORE_INVALID/);sh.rows[1][1]=old;
 store.read();sh.rows.pop();assert.throws(()=>store.read(),/SESSION_STORE_INVALID/);
});
test('B2 prefix reuse observes correctly chained new revocation',f=>{
 f.call('ui_context');const store=f.x.juogSessionStoreB2_(f.x.getSpreadsheet_(),f.c);
 const before=store.read(),open=before.events[0];
 store.append({...open,kind:'REVOKE',jti:'offline-new-revocation'});
 assert.equal(store.read().events.at(-1).kind,'REVOKE');
 assert.equal(f.call('ui_context').error,'SESSION_REVOKED');
});
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
test('recovery lists saved UUID version and audit after browser loss',f=>{const p=f.payload();assert.equal(f.save(p).ok,true);const q={registration_id:p.registration_id,facility_code:'TEST01',crf_type:p.crf_type,visit:p.visit};const r=f.call('recovery_status',q);assert.equal(r.recovery.state,'SAVED');assert.equal(r.recovery.operations[0].uuid,p.submission_id);assert.equal(r.recovery.operations[0].version,1);assert.equal(r.recovery.operations[0].audit_verified,true);assert.equal(f.call('recovery_retry',{...q,submission_id:p.submission_id}).ok,false);assert.equal(f.tables.CRF_30d.rows.length,2);});
test('recovery retries stored payload same UUID using new signed request',f=>{const p=f.payload();f.drop('CRFSubmissionAudit');assert.equal(f.save(p).ok,false);f.drop('');const q={registration_id:p.registration_id,facility_code:'TEST01',crf_type:p.crf_type,visit:p.visit};const r=f.call('recovery_status',q);assert.equal(r.recovery.state,'RETRY_ALLOWED');assert(!JSON.stringify(r).includes('day30_labs_raw'));const saved=f.call('recovery_retry',{...q,submission_id:p.submission_id});assert.equal(saved.ok,true,JSON.stringify(saved));assert.equal(saved.record_version,1);assert.equal(f.call('recovery_status',q).recovery.state,'SAVED');assert.equal(f.tables.CRF_30d.rows.length,2);assert.equal(f.tables.CRFSubmissionAudit.rows.length,2);});
test('recovery cannot substitute payload or invent UUID or mix visit',f=>{const p=f.payload();f.drop('CRF_30d');assert.equal(f.save(p).ok,false);f.drop('');const q={registration_id:p.registration_id,crf_type:p.crf_type,visit:p.visit};assert.equal(f.call('recovery_retry',{...q,submission_id:p.submission_id,payload:{}}).error,'REQUEST_INVALID');assert.equal(f.call('recovery_retry',{...q,submission_id:'guessed'}).ok,false);assert.equal(f.call('recovery_retry',{...q,crf_type:'day90',visit:'90d',submission_id:p.submission_id}).ok,false);assert.equal(f.tables.CRF_30d.rows.length,1);});
test('recovery missing canonical payload or corrupted digest stops',f=>{const p=f.payload();f.drop('CRF_30d');f.save(p);f.drop('');const row=f.tables.R1_Operations.rows[1],event=JSON.parse(row[1]);delete event.payload;row[1]=JSON.stringify(event);row[2]=hash(row[1]);const q={registration_id:p.registration_id,crf_type:p.crf_type,visit:p.visit};assert.equal(f.call('recovery_status',q).recovery.state,'NEEDS_RECONCILIATION');assert.equal(f.call('recovery_retry',{...q,submission_id:p.submission_id}).ok,false);});
test('recovery owner revocation and expired assertion deny',f=>{const p=f.payload();f.save(p);const q={registration_id:p.registration_id,crf_type:p.crf_type,visit:p.visit};f.tables.R1_CaseOwners.rows[1][2]='other';assert.equal(f.call('recovery_status',q).error,'SUBJECT_FORBIDDEN');f.tables.R1_CaseOwners.rows[1][2]='fictional-user';const e=f.envelope('recovery_status',q);f.advance(15000);assert.equal(f.x.juogPr15Entry_(e,f.c).error,'AUTH_EXPIRED');assert.equal(f.call('session_revoke').revoked,true);assert.equal(f.call('recovery_status',q).error,'SESSION_REVOKED');});
test('clinical rejection cannot append body version audit or operation intent',f=>{const p=f.payload();delete p.data.day30_visit_date;const before=['CRF_30d','CRFSubmissionAudit','R1_Operations'].map(n=>JSON.stringify(f.tables[n].rows));const r=f.save(p);assert.equal(r.error,'CLINICAL_VALIDATION_FAILED');assert.deepEqual(['CRF_30d','CRFSubmissionAudit','R1_Operations'].map(n=>JSON.stringify(f.tables[n].rows)),before);});
test('clinically complete operated fixture saves v1 and correction with old version retained',f=>{const p=JSON.parse(fs.readFileSync(path.join(root,'clinical_contract/operated_fixture.json'),'utf8'));assert.equal(f.save(p).ok,true);const q=copy(p);q.submission_id='operated-v2';q.submission_kind='訂正報告';q.correction_reason='fictional correction';q.data.blood_loss_ml=10;assert.equal(f.save(q,1).ok,true);assert.equal(f.tables.CRF_30d.rows.length,3);assert.equal(f.tables.CRFSubmissionAudit.rows.length,3);});
test('all visit clinical failures leave CRF audit intent and notification state unchanged',f=>{for(const [type,visit] of [['perioperative_30d','30d'],['day90','90d'],...['6m','9m','12m','15m','18m','21m','24m'].map(v=>['followup',v])]){const p=f.payload(type,visit);p.data.vital_status=null;const names=['CRF_30d','CRF_90d','CRF_Followup','CRFSubmissionAudit','R1_Operations'];const before=names.map(n=>JSON.stringify(f.tables[n].rows));assert.equal(f.save(p).error,'CLINICAL_VALIDATION_FAILED');assert.deepEqual(names.map(n=>JSON.stringify(f.tables[n].rows)),before);}});
test('recovery payload digest mismatch and untracked rows prevent retry',f=>{const p=f.payload();f.drop('CRF_30d');f.save(p);f.drop('');const q={registration_id:p.registration_id,crf_type:p.crf_type,visit:p.visit};const row=f.tables.R1_Operations.rows[1],event=JSON.parse(row[1]);event.payload.data.day30_visit_date='2026-02-10';row[1]=JSON.stringify(event);row[2]=hash(row[1]);assert.equal(f.call('recovery_status',q).recovery.state,'NEEDS_RECONCILIATION');assert.equal(f.call('recovery_retry',{...q,submission_id:p.submission_id}).ok,false);assert.equal(f.tables.CRF_30d.rows.length,1);});
test('recovery jti replay fails while fresh signature can reconcile',f=>{const p=f.payload();f.save(p);const q={registration_id:p.registration_id,crf_type:p.crf_type,visit:p.visit};const e=f.envelope('recovery_status',q);assert.equal(f.x.juogPr15Entry_(e,f.c).ok,true);assert.equal(f.x.juogPr15Entry_(e,f.c).error,'ASSERTION_REPLAY');assert.equal(f.call('recovery_status',q).recovery.state,'SAVED');});

function sectionQ(type='perioperative_30d',visit='30d') {return {registration_id:'JUOG-901',facility_code:'TEST01',crf_type:type,visit};}
function sectionOp(id='fictional-section-uuid-0001',changes={}) {return {...sectionQ(),section:'1',record_version:0,expected_revision:0,operation_id:id,data:{peri_registration_id:{type:'value',value:'JUOG-901'}},...changes};}
test('section draft debounce target is a single audited append with immutable replay',f=>{
 const q=sectionOp();let r=f.call('save_section',q);assert.equal(r.ok,true,JSON.stringify(r));assert.equal(r.receipt.revision,1);assert.equal(r.audit_verified,true);
 assert.equal(f.call('save_section',q).existing,true);assert.equal(f.tables.R1_DraftEvents.rows.length,2);
 assert.equal(f.tables.Registry.rows.length,2);assert.equal(f.tables.CRF_30d.rows.length,1);assert.equal(f.tables.R1_Operations.rows.length,1);
 const resumed=f.call('get_sections',sectionQ());assert.deepEqual(resumed.sections['1'].data,q.data);
});
test('section stale-tab conflicts and same UUID different payload deny without audit append',f=>{
 const q=sectionOp();f.call('save_section',q);const count=f.tables.R1_DraftEvents.rows.length;
 assert.equal(f.call('save_section',sectionOp('different-operation-0002')).error,'DRAFT_CONFLICT');
 q.data.peri_reporter_email={type:'value',value:'fictional@example.invalid'};
 assert.equal(f.call('save_section',q).error,'DRAFT_CONFLICT');assert.equal(f.tables.R1_DraftEvents.rows.length,count);
});
test('section silent append failure safe same UUID retry with fresh assertion',f=>{
 const q=sectionOp();f.drop('R1_DraftEvents');assert.equal(f.call('save_section',q).error,'DRAFT_WRITE_UNCONFIRMED');f.drop('');
 const e=f.envelope('save_section',q);assert.equal(f.x.juogPr15Entry_(e,f.c).ok,true);assert.equal(f.x.juogPr15Entry_(e,f.c).error,'ASSERTION_REPLAY');assert.equal(f.call('save_section',q).existing,true);
});
test('section lost response after append expiry resumes canonical server data',f=>{
 const q=sectionOp();f.expireOn('R1_DraftEvents');assert.equal(f.call('save_section',q).ok,false);assert.equal(f.tables.R1_DraftEvents.rows.length,2);f.expireOn('');
 assert.equal(f.call('get_sections',sectionQ()).sections['1'].operation_id,q.operation_id);assert.equal(f.call('save_section',q).existing,true);
});
test('section all nine visits are isolated and no wrong field or arbitrary session restore',f=>{
 for(const [t,v,p] of [['perioperative_30d','30d','peri'],['day90','90d','d90'],...['6m','9m','12m','15m','18m','21m','24m'].map(v=>['followup',v,'fu'])]){
  const q=sectionOp('fictional-section-'+v,{...sectionQ(t,v),data:{[p+'_registration_id']:{type:'value',value:'JUOG-901'}}});assert.equal(f.call('save_section',q).ok,true,JSON.stringify(q));
  assert.equal(Object.keys(f.call('get_sections',sectionQ(t,v)).sections).length,1);
 }
 const q=sectionOp('fictional-bad-field',{section:'2',data:{auth_connect_halted:{type:'value',value:false}}});assert.equal(f.call('save_section',q).error,'DRAFT_DATA_INVALID');
});
test('section ownership ACL session revocation and transferred cases reject',f=>{
 const q=sectionOp();f.call('save_section',q);f.tables.R1_CaseOwners.rows[1][2]='someone-else';assert.equal(f.call('get_sections',sectionQ()).error,'SUBJECT_FORBIDDEN');f.tables.R1_CaseOwners.rows[1][2]='fictional-user';
 const row=f.tables.R1_DraftEvents.rows[1],e=JSON.parse(row[0]);e.actor='previous-owner';row[0]=JSON.stringify(e);row[1]=hash(row[0]);assert.equal(f.call('get_sections',sectionQ()).error,'SUBJECT_FORBIDDEN');
 f.call('session_revoke');assert.equal(f.call('save_section',q).error,'SESSION_REVOKED');
});
test('section old drafts never resurrect after official version and journal corruption fails',f=>{
 const q=sectionOp();f.call('save_section',q);assert.equal(f.save(f.payload()).ok,true);assert.deepEqual(f.call('get_sections',sectionQ()).sections,{});assert.equal(f.call('save_section',q).error,'DRAFT_CONFLICT');
 f.tables.R1_DraftEvents.rows[1][1]='corrupt';assert.equal(f.call('get_sections',sectionQ()).error,'DRAFT_STORE_INVALID');
});
test('section pending official transaction blocks new draft and preserves zero false null',f=>{
 const q=sectionOp();q.data.peri_reporter_email={type:'value',value:''};assert.equal(f.call('save_section',q).ok,true);
 const q2=sectionOp('fictional-section-null',{section:'2',data:{peri_op_completed:{type:'value',value:null},peri_bleeding:{type:'value',value:0}}});assert.equal(f.call('save_section',q2).ok,true);
 f.drop('CRF_30d');assert.equal(f.save(f.payload()).ok,false);f.drop('');assert.equal(f.call('get_sections',sectionQ()).error,'PENDING_OPERATION');
});

test('section date identity fields and expired signatures fail before any draft append',f=>{
 const before=f.tables.R1_DraftEvents.rows.length;
 for(const data of [{peri_op_date:{type:'date',value:'2026-02-30'}},{auth_connect_halted:{type:'value',value:false}}])assert.equal(f.call('save_section',sectionOp('invalid-data-operation',{section:'2',data})).error,'DRAFT_DATA_INVALID');
 assert.equal(f.call('save_section',sectionOp('invalid-case-operation',{data:{peri_registration_id:{type:'value',value:'JUOG-902'}}})).error,'DRAFT_DATA_INVALID');
 const e=f.envelope('save_section',sectionOp());f.advance(15000);assert.equal(f.x.juogPr15Entry_(e,f.c).error,'AUTH_EXPIRED');assert.equal(f.tables.R1_DraftEvents.rows.length,before);
});
fs.writeFileSync(path.join(root,'integration_evidence/endpoint_results.json'),JSON.stringify({mode:'OFFLINE_IN_MEMORY_REAL_SOURCE',test_groups:tests.length,tests,formal_uat_pass_delta:0,independent_qa_approved:false},null,2)+'\n');
test('draft read and retry reject structurally invalid stored values without append',f=>{
 const q=sectionOp();assert.equal(f.call('save_section',q).ok,true);
 const original=copy(f.tables.R1_DraftEvents.rows[1]);
 for(const data of [
  {peri_registration_id:{type:'value',value:'JUOG-902'}},
  {peri_reporter_email:{type:'value',value:'other@example.invalid'}},
  {peri_correction_reason:{type:'value',value:'患者氏名 テスト太郎'}},
  {peri_registration_id:{type:'date',value:'2026-02-30'}},
  {peri_registration_id:{type:'unsupported',value:'JUOG-901'}}
 ]){
  const e=JSON.parse(original[0]);e.data=data;e.digest=hash(f.x.pr15Canonical_(data));
  const json=JSON.stringify(e);f.tables.R1_DraftEvents.rows[1]=[json,hash(json)];
  assert.equal(f.call('get_sections',sectionQ()).error,'DRAFT_STORE_INVALID');
  assert.equal(f.call('save_section',q).error,'DRAFT_STORE_INVALID');
  assert.equal(f.tables.R1_DraftEvents.rows.length,2);assert.equal(f.tables.CRF_30d.rows.length,1);
  assert.equal(f.tables.R1_Operations.rows.length,1);assert.equal(f.tables.CRFSubmissionAudit.rows.length,1);
 }
 f.tables.R1_DraftEvents.rows[1]=original;
 assert.equal(f.call('get_sections',sectionQ()).ok,true);
 assert.equal(f.call('save_section',q).existing,true);
});
test('space-separated explicit identifier labels denied before clinical or draft writes',f=>{
 for(const text of ['患者氏名 テスト太郎','カルテ番号 FAKE123','生年月日 1980年1月2日','患者氏名　テスト太郎']){
  const p=f.payload();p.data.free_text=text;assert.equal(f.save(p).error,'DIRECT_IDENTIFIER_NOT_ALLOWED');
  const q=sectionOp();q.data.peri_correction_reason={type:'value',value:text};
  assert.equal(f.call('save_section',q).error,'DRAFT_DATA_INVALID');
 }
 assert.equal(f.tables.R1_DraftEvents.rows.length,1);assert.equal(f.tables.R1_Operations.rows.length,1);
 assert.equal(f.tables.CRF_30d.rows.length,1);assert.equal(f.tables.CRFSubmissionAudit.rows.length,1);
});
test('pending recovery scans CRFs once and observes changes on the next request',f=>{
 const p=f.payload();f.expireOn('R1_Operations');assert.equal(f.save(p).error,'AUTH_EXPIRED');f.expireOn('');
 const q={registration_id:p.registration_id,facility_code:'TEST01',crf_type:p.crf_type,visit:p.visit};
 const before=copy(f.metrics.reads),writes=f.tables.R1_Operations.rows.length;
 assert.equal(f.call('recovery_status',q).recovery.state,'RETRY_ALLOWED');
 for(const name of ['CRF_30d','CRF_90d','CRF_Followup'])assert.equal(f.metrics.reads[name]-before[name],1);
 assert.equal(f.tables.R1_Operations.rows.length,writes);
 assert.equal(f.tables.CRF_30d.rows.length,1);assert.equal(f.tables.CRFSubmissionAudit.rows.length,1);
 // A later request must see new/corrupt cells, never a previous record snapshot.
 f.row('CRF_30d',{submission_id:'untracked',registration_id:p.registration_id,record_key:p.record_key,record_version:1,facility_code:'TEST01',payload_json:'{}'});
 assert.equal(f.call('recovery_status',q).recovery.state,'NEEDS_RECONCILIATION');
 assert.equal(f.call('recovery_retry',{...q,submission_id:p.submission_id}).ok,false);
 assert.equal(f.tables.CRF_30d.rows.length,2);assert.equal(f.tables.CRFSubmissionAudit.rows.length,1);
});
console.log('ALL '+tests.length+' GROUPS PASSED');

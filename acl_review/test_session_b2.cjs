const fs=require('fs'),vm=require('vm'),crypto=require('crypto'),assert=require('assert/strict');
const root=__dirname,source=fs.readFileSync(root+'/bundle/isolated_review_bundle.gs','utf8');
const hash=s=>crypto.createHash('sha256').update(s).digest('hex');
let now=1794484800,locked=false,lockFail=false,writeFail=false,delay=0;
const c={environment:'ISOLATED_TEST',approvalRef:'LOCAL',backupVerified:true,qaApproved:true,fictionalBaselineVerified:true,notificationsDisabled:true,spreadsheetId:'1Hd6EHDPZe8zGcDbILkaBLubgF5atfAzRfpPSN5LemiU',approvedSpreadsheetId:'1Hd6EHDPZe8zGcDbILkaBLubgF5atfAzRfpPSN5LemiU',allRoutesReviewed:true,schemaParityApproved:true,signingKey:'x'.repeat(40),bridgeIssuer:'local',audience:'localgas',oidcIssuer:'https://idp.invalid',resumeDerivationKey:'r'.repeat(40),draftPepper:'p'.repeat(40),sessionPolicy:'isolated_gas_session_b2',sessionStoreGeneration:'synthetic-generation',sessionStoreApproved:true};
const hs=new Function(source.slice(source.indexOf('const REGISTRY_HEADERS ='),source.indexOf('function authorizeJuogAction_'))+';return {Registry:REGISTRY_HEADERS,Screening:SCREENING_HEADERS,CRF_Drafts:CRF_DRAFT_HEADERS,MDTReviews:MDT_REVIEW_HEADERS,CRF_30d:CRF_BASE_HEADERS};')();
const baseline=Object.fromEntries(Object.entries(hs).map(([k,h])=>[k,[h]]));
const make=(h,o)=>h.map(k=>o[k]??'');baseline.Registry.push(make(hs.Registry,{registration_id:'JUOG-001',status:'ACTIVE',facility_code:'TEST01',screening_id:'JUOG-SCR-001'}));
const raw=JSON.stringify(baseline),journal=[['batch_id','kind','part','total','sha256','data'],['base','baseline',0,1,hash(raw),raw],['base','baseline','SEALED',1,hash(raw),'']];
let events=[['sequence','event_json','chain_sha256']];
const acl=[['issuer','subject','user_id','enabled','role','facility_ids_json','valid_until'],[c.oidcIssuer,'SYNTHETIC','TEST-USER',true,'facility','["TEST01"]','2026-11-19T14:59:00Z']];
const props=new Map([['JUOG_B2_HEAD_'+c.spreadsheetId,'0:'+hash('JUOG-B2|'+c.spreadsheetId+'|synthetic-generation')]]);
const sheet=rows=>({getRange:()=>({getValues:()=>[rows[0]]}),getDataRange:()=>({getValues:()=>structuredClone(rows)}),appendRow:r=>{if(writeFail)throw Error('INJECTED_IO');rows.push(structuredClone(r));if(rows===journal)now+=delay;}});
const ss={getSheetByName:n=>n==='D3_Journal'?sheet(journal):n==='V3_Users'?sheet(acl):n==='V3_SessionEvents'&&events?sheet(events):null};
function context(){class Clock extends Date{constructor(...a){super(...(a.length?a:[now*1000]));}static now(){return now*1000;}}
 const x=vm.createContext({ScriptApp:{getScriptId:()=>'11wSp4ePaP5b5A2b5ITZZSZa3YTe-Ex-Tu6oGlEkkRfkPrMCA4deVSZDy'},Date:Clock,JSON,Object,Array,String,Number,Error,Math,Set,PropertiesService:{getScriptProperties:()=>({getProperty:k=>props.get(k),setProperty:(k,v)=>props.set(k,v)})},SpreadsheetApp:{openById:()=>ss,flush:()=>{}},LockService:{getScriptLock:()=>({tryLock:()=>{if(locked||lockFail)return false;locked=true;return true;},releaseLock:()=>locked=false})},Utilities:{getUuid:()=>crypto.randomUUID(),formatDate:()=>new Date(now*1000).toISOString().slice(0,10),Charset:{UTF_8:'utf8'},DigestAlgorithm:{SHA_256:'sha256'},computeDigest:(_,s)=>[...crypto.createHash('sha256').update(s).digest()],computeHmacSha256Signature:(s,k)=>[...crypto.createHmac('sha256',k).update(s).digest()],base64EncodeWebSafe:b=>Buffer.from(b).toString('base64url'),base64DecodeWebSafe:s=>[...Buffer.from(s,'base64url')],newBlob:b=>({getDataAsString:()=>Buffer.from(b).toString('utf8')})}});vm.runInContext(source,x);return x;}
let x=context(),sid=hash('synthetic-token'),origin=now;
function env(action='ui_context',payload={id:'context',action:'ui_context',payload:{registration_id:'JUOG-001'}},changes={}){
 const request_json=JSON.stringify({action,payload}),claims={v:2,iss:c.bridgeIssuer,aud:c.audience,oidc_issuer:c.oidcIssuer,sub:'SYNTHETIC',iat:now,exp:now+15,request_hash:hash(request_json),session:{sid,jti:crypto.randomUUID().replaceAll('-',''),token_iat:origin,deadline:origin+3600},...changes};
 const encoded=Buffer.from(JSON.stringify(claims)).toString('base64url');return {request_json,identity_assertion:encoded+'.'+crypto.createHmac('sha256',c.signingKey).update(encoded).digest('base64url')};}
const call=e=>x.juogUnifiedIsolationEntryV3_(e,c),checks=[];
function test(name,f){f();checks.push(name);}
test('actual Python signer to GAS session and individual ACL',()=>{
 const py=`import sys,json
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,sys.argv[1])
from auth_bridge import signed_request
x=json.load(sys.stdin)
class User(dict):
 is_logged_in=True
u=User(iss=x['issuer'],sub='SYNTHETIC',aud='client',iat=x['now'],exp=x['now']+7200,nonce='synthetic-nonce')
c=dict(oidc_issuer=x['issuer'],oidc_client_id='client',signing_key=x['key'],bridge_issuer='local',audience='localgas',session_policy='isolated_gas_session_b2',session_environment='JUOG_AUTH04_ISOLATED_TEST01',session_b_safety_review_approved=True,session_b_limited_execution_approved=True,session_store_generation='synthetic-generation')
st=SimpleNamespace(user=u,secrets={'juog_identity_bridge':c})
with patch('auth_bridge.time.time',return_value=x['now']):
 print(json.dumps(signed_request(st,'ui_context',{'id':'context','action':'ui_context','payload':{'registration_id':'JUOG-001'}})))`;
 const result=require('child_process').spawnSync('python',['-c',py,root+'/python_candidate'],{input:JSON.stringify({issuer:c.oidcIssuer,key:c.signingKey,now}),encoding:'utf8'});
 assert.equal(result.status,0);assert.equal(call(JSON.parse(result.stdout)).ok,true);
});
test('replay rejected across a fresh GAS process',()=>{const e=env();assert.equal(call(e).ok,true);x=context();assert.equal(call(e).error,'ASSERTION_REPLAY');});
test('revocation rejects already-issued valid envelope',()=>{const pending=env();assert.equal(call(env('session_revoke',{})).revoked,true);assert.equal(call(pending).error,'SESSION_REVOKED');});
test('revoked token cannot reopen after restart',()=>{x=context();assert.equal(call(env()).error,'SESSION_REVOKED');});
sid=hash('new-token');
test('new verified token can start a separate session',()=>assert.equal(call(env()).ok,true));
test('unregistered identity denied without business writes',()=>assert.equal(call(env(undefined,undefined,{sub:'UNKNOWN',session:{sid:hash('unknown-token'),jti:crypto.randomUUID().replaceAll('-',''),token_iat:origin,deadline:origin+3600}})).error,'ACL_DENIED'));
test('other facility denied',()=>{acl[1][5]='["OTHER"]';assert.equal(call(env()).error,'ACL_DENIED');acl[1][5]='["TEST01"]';});
test('invalid role denied',()=>{acl[1][4]='owner';assert.equal(call(env()).ok,false);acl[1][4]='facility';});
test('revoked ACL immediate denial',()=>{acl[1][3]=false;assert.equal(call(env()).error,'ACL_DENIED');acl[1][3]=true;});
test('signed business request blocked before separate AUTH04 approval',()=>assert.equal(call(env('prepare_request',{action:'save_crf',payload:{}})).error,'AUTH04_EXECUTION_NOT_APPROVED'));
test('unsigned save API denied',()=>assert.equal(call({request_json:'{"action":"save_crf","payload":{}}'}).error,'AUTH_REQUIRED'));
test('delayed expired envelope rejected',()=>{const e=env();now+=15;assert.equal(call(e).error,'AUTH_EXPIRED');});
test('concurrent request cannot enter while lock held',()=>{locked=true;assert.equal(call(env()).error,'LOCK_TIMEOUT');locked=false;});
test('missing store denied',()=>{const saved=events;events=null;assert.equal(call(env()).error,'SESSION_STORE_UNAVAILABLE');events=saved;});
test('truncated store rejected against independent head',()=>{const row=events.pop();assert.equal(call(env()).error,'SESSION_STORE_INVALID');events.push(row);});
test('v1 downgrade rejected in B2 mode',()=>assert.equal(call(env(undefined,undefined,{v:1})).error,'SESSION_INVALID'));
test('session deadline never extends on restart',()=>{now=origin+3600;assert.equal(call(env()).error,'SESSION_INVALID');now=origin+30;});
test('expiry during chunk write prevents seal',()=>{const auth=x.juogV3DecodeBridge_(env(),c),who=x.juogV3ReadIndividualAcl_(ss,c.oidcIssuer,'SYNTHETIC');locked=true;try{const g=x.juogSessionGateB2_(ss,c,auth,who),st=x.juogDomainSheetsStoreV3_(ss,hash,()=>crypto.randomUUID(),g.guard);delay=16;assert.throws(()=>st.appendRequest({id:'delayed'}),/AUTH_EXPIRED/);assert.notEqual(journal[journal.length-1][2],'SEALED');}finally{locked=false;delay=0;}});
test('uncertain store append closes subsequent requests',()=>{writeFail=true;assert.equal(call(env()).ok,false);writeFail=false;assert.equal(call(env()).error,'SESSION_STORE_INVALID');});
const result={scope:'Offline actual GAS decoder, endpoint and persistent-store adapter with synthetic Sheets/clock/lock; no Google login or live GAS execution',checks,count:checks.length,result:'PASS',formal_uat_delta:0};
fs.writeFileSync(root+'/../uat_evidence/session_b2_regression.json',JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result,null,2));

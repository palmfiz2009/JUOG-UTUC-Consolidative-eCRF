const fs=require('fs'),vm=require('vm'),crypto=require('crypto'),assert=require('assert/strict');
const root=__dirname+'/../canonical_v9_integration',source=fs.readFileSync(__dirname+'/bundle_recovery_candidate.gs','utf8');
const hash=s=>crypto.createHash('sha256').update(s).digest('hex');
let now=1794484800,locked=false,lockFail=false,writeFail=false,delay=0;
const c={environment:'ISOLATED_TEST',approvalRef:'LOCAL',backupVerified:true,qaApproved:true,fictionalBaselineVerified:true,notificationsDisabled:true,spreadsheetId:'1Hd6EHDPZe8zGcDbILkaBLubgF5atfAzRfpPSN5LemiU',approvedSpreadsheetId:'1Hd6EHDPZe8zGcDbILkaBLubgF5atfAzRfpPSN5LemiU',allRoutesReviewed:true,schemaParityApproved:true,signingKey:'x'.repeat(40),bridgeIssuer:'local',audience:'localgas',oidcIssuer:'https://idp.invalid',resumeDerivationKey:'r'.repeat(40),draftPepper:'p'.repeat(40),sessionPolicy:'isolated_gas_session_b2',sessionStoreGeneration:'synthetic-generation',sessionStoreApproved:true};
c.sessionExecutionStage='AUTH_CONNECT';c.authConnectReviewApproved=true;c.authConnectReviewRef='OFFLINE_REVIEW';c.signingKey=crypto.randomBytes(32).toString('hex');
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
function env(action='ui_context',payload={id:'context',action:'ui_context',payload:{registration_id:''}},changes={}){
 const request_json=JSON.stringify({action,payload}),claims={v:2,iss:c.bridgeIssuer,aud:c.audience,oidc_issuer:c.oidcIssuer,sub:'SYNTHETIC',iat:now,exp:now+15,request_hash:hash(request_json),session:{sid,generation:c.sessionStoreGeneration,jti:crypto.randomUUID().replaceAll('-',''),token_iat:origin,deadline:origin+3600},...changes};
 const encoded=Buffer.from(JSON.stringify(claims)).toString('base64url');return {request_json,identity_assertion:encoded+'.'+crypto.createHmac('sha256',c.signingKey).update(encoded).digest('base64url')};}
const call=e=>x.juogUnifiedIsolationEntryV3_(e,c),checks=[];
function test(name,f){f();checks.push(name);}

assert.equal(hash(source),'8f26e2985af43299a9d9c6a18a981bfe3d2bc1b5a8739463f7faccb39b04cc84');
const originalJournal=JSON.stringify(journal);
const py=`import sys,json
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,sys.argv[1])
from canonical_v9_bridge import build
from juog_common import redact_draft_identifiers
x=json.load(sys.stdin)
class User(dict):is_logged_in=True
u=User(iss=x['issuer'],sub='SYNTHETIC',aud='client',iat=x['now'],exp=x['now']+7200,nonce='synthetic-nonce')
c=dict(oidc_issuer=x['issuer'],oidc_client_id='client',signing_key=x['key'],bridge_issuer='local',audience='localgas',session_policy='isolated_gas_session_b2',session_environment='JUOG_AUTH04_ISOLATED_TEST01',session_b_safety_review_approved=True,session_b_limited_execution_approved=True,session_store_generation='synthetic-generation')
n=SimpleNamespace(user=u,secrets={'juog_identity_bridge':c})
with patch('uat_b2_auth_bridge.time.time',return_value=x['now']):
 e,op=build(n,'save_crf',{'payload':x['payload']},redact_draft_identifiers,{}, {})
 print(json.dumps(e))`;
let e;
test('canonical Python envelope accepted by pinned V9 decoder but business denied',()=>{
 const result=require('child_process').spawnSync('python',['-c',py,root],{input:JSON.stringify({issuer:c.oidcIssuer,key:c.signingKey,now,payload:JSON.parse(fs.readFileSync(root+'/canonical_fixture.json')).payload}),encoding:'utf8'});
 assert.equal(result.status,0);e=JSON.parse(result.stdout);assert.equal(call(e).error,'AUTH04_EXECUTION_NOT_APPROVED');
});
test('same canonical signature replay denied',()=>assert.equal(call(e).error,'ASSERTION_REPLAY'));
test('context approved for exact facility',()=>assert.equal(call(env()).ok,true));
test('unregistered principal rejected',()=>assert.equal(call(env(undefined,undefined,{sub:'UNKNOWN'})).error,'ACL_DENIED'));
test('wrong role rejected',()=>{acl[1][4]='invalid_role';assert.equal(call(env()).error,'ACL_DENIED');acl[1][4]='facility';});
test('other facility rejected',()=>{acl[1][5]='["OTHER"]';assert.equal(call(env()).error,'ACL_DENIED');acl[1][5]='["TEST01"]';});
test('revocation rejects already signed context',()=>{const pending=env();assert.equal(call(env('session_revoke',{})).revoked,true);assert.equal(call(pending).error,'SESSION_REVOKED');});
test('expired envelope rejected',()=>{const pending=env();now+=15;assert.equal(call(pending).error,'AUTH_EXPIRED');});
test('business journal unchanged',()=>assert.equal(JSON.stringify(journal),originalJournal));
const out={mode:'OFFLINE_MODIFIED_RECOVERY_CANDIDATE_AUTH_CONNECT_REGRESSION_SYNTHETIC_SHEETS_CLOCK_IDENTITY',checks,passed:true,count:checks.length,business_network_calls:0,formal_pass_delta:0};
fs.writeFileSync(__dirname+'/signed_scope_regression.json',JSON.stringify(out,null,2)+'\n');console.log(JSON.stringify(out));

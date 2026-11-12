const fs=require('fs'),vm=require('vm'),crypto=require('crypto'),assert=require('assert/strict'),path=require('path');
const source=fs.readFileSync(path.join(__dirname,'mode_admin.gs'),'utf8');
// Synthetic journal only: no live data or raw principal is loaded.
const journal=[['SYNTHETIC_OFFLINE_JOURNAL']];
const script='11wSp4ePaP5b5A2b5ITZZSZa3YTe-Ex-Tu6oGlEkkRfkPrMCA4deVSZDy',sheet='1Hd6EHDPZe8zGcDbILkaBLubgF5atfAzRfpPSN5LemiU';
const hash=s=>crypto.createHash('sha256').update(s).digest('hex');
const expectedJournalHash='1c783409e5f4cc1057de2d0de76ac379b4bb73e74f665438cfb595e9a42731b2';
const good={environment:'ISOLATED_TEST',spreadsheetId:sheet,approvedSpreadsheetId:sheet,sessionPolicy:'isolated_gas_session_b2',sessionStoreGeneration:'d72bcf33-423d-4c4d-862d-2e2d69bc3edf',sessionExecutionStage:'AUTH_CONNECT',sessionStoreApproved:true,authConnectReviewApproved:true,authConnectReviewRef:'offline-review',approvalRef:'offline-pi',notificationsDisabled:true,backupVerified:true,fictionalBaselineVerified:true,qaApproved:true,allRoutesReviewed:false,schemaParityApproved:false,unchangedSentinel:42};
function env(options={}){
 let raw=JSON.stringify({...good,...options.config}),writes=0,gets=0,opened=0,released=0;const logs=[];
 const acl=[['issuer','subject','user_id','enabled','role','facility_ids_json','valid_until'],['https://accounts.google.com','SYNTHETIC_OFFLINE_ONLY','UAT_TEST01_PI_01',true,'facility','["TEST01"]','2026-11-19T23:59:00+09:00']];if(options.badAcl)acl[1][4]='admin';if(options.aclMutation)options.aclMutation(acl);
 const props={getProperty:k=>{assert.equal(k,'UNIFIED_ISOLATION_CONFIG');gets++;if(options.readbackMismatch&&gets===2)return 'mismatch';return raw;},setProperty:(k,v)=>{assert.equal(k,'UNIFIED_ISOLATION_CONFIG');writes++;if(options.alwaysWriteFail)throw Error('SECRET_SENTINEL');raw=v;if(options.throwAfterFirstWrite&&writes===1)throw Error('SECRET_SENTINEL');}};
 class Clock extends Date{static now(){return Date.parse(options.expired?'2026-11-19T15:00:00Z':'2026-11-13T00:00:00Z')}}
 const c={Date:Clock,console:{info:x=>logs.push(x)},ScriptApp:{getScriptId:()=>options.badScript?'wrong':script},PropertiesService:{getScriptProperties:()=>props},LockService:{getScriptLock:()=>({tryLock:()=>!options.lockFail,releaseLock:()=>released++})},SpreadsheetApp:{openById:id=>{assert.equal(id,sheet);opened++;return {getSheetByName:name=>({getDataRange:()=>({getValues:()=>name==='V3_Users'?acl:options.badJournal?[['changed']]:journal})})}}},Utilities:{DigestAlgorithm:{SHA_256:'sha256'},Charset:{UTF_8:'utf8'},computeDigest:(_,s)=>{
  // Explicitly synthetic identity pin substitution: no real claims are used.
  const synthetic=s.startsWith('["JUOG-ACL-PROPOSAL-v1",');const hex=synthetic&&!options.badPrincipal?'f0ea0ddb132e96bbd08cba4e37dc38609b73db5740530a05225c5acb6cab798f':s===JSON.stringify(journal)?expectedJournalHash:hash(s);
  return Array.from(Buffer.from(hex,'hex'),b=>b>127?b-256:b);
 }}};vm.createContext(c);vm.runInContext(source,c);return {c,logs,state:()=>({raw:JSON.parse(raw),writes,gets,opened,released})};
}
let passed=0;function test(name,f){f();passed++;}
test('enable fixed scope preserves unrelated config',()=>{let e=env();assert.equal(e.c.juogEnableNegativeAuth04(),true);let s=e.state();assert.equal(s.raw.sessionExecutionStage,'AUTH04_APPROVED');assert.equal(s.raw.unchangedSentinel,42);assert.equal(s.raw.allRoutesReviewed,false);assert.equal(s.raw.schemaParityApproved,false);assert.equal(s.writes,1);assert.equal(s.released,1)});
for(const options of [{badScript:true},{badAcl:true},{badPrincipal:true},{badJournal:true},{config:{sessionExecutionStage:'AUTH04_APPROVED'}},{config:{authConnectReviewRef:{x:1}}},{config:{notificationsDisabled:false}}])test('prewrite guard',()=>{const e=env(options);assert.equal(e.c.juogEnableNegativeAuth04(),false);assert.equal(e.state().writes,0);assert.equal(e.logs.at(-1),'AUTH04_MODE_CHANGE_REFUSED_NO_WRITE')});
test('lock refusal no property or sheet access',()=>{const e=env({lockFail:true});assert.equal(e.c.juogEnableNegativeAuth04(),false);assert.equal(e.state().gets,0);assert.equal(e.state().opened,0)});
test('write took effect then threw rolls back restrictive',()=>{const e=env({throwAfterFirstWrite:true});assert.equal(e.c.juogEnableNegativeAuth04(),false);assert.equal(e.state().raw.sessionExecutionStage,'AUTH_CONNECT');assert.equal(e.state().raw.auth04ScopeReviewed,false);assert.equal(e.logs.at(-1),'AUTH04_MODE_FAILED_RESTRICTIVE_STATE_VERIFIED');assert(!e.logs.join('').includes('SECRET_SENTINEL'))});
test('readback mismatch rolls back restrictive',()=>{const e=env({readbackMismatch:true});assert.equal(e.c.juogEnableNegativeAuth04(),false);assert.equal(e.state().raw.sessionExecutionStage,'AUTH_CONNECT');assert.equal(e.state().writes,2)});
test('disable does not depend on business journal',()=>{const e=env({config:{sessionExecutionStage:'AUTH04_APPROVED'},badJournal:true});assert.equal(e.c.juogDisableNegativeAuth04(),true);assert.equal(e.state().raw.sessionExecutionStage,'AUTH_CONNECT');assert.equal(e.state().opened,0)});
test('failed disable must report state unknown',()=>{const e=env({config:{sessionExecutionStage:'AUTH04_APPROVED'},alwaysWriteFail:true});assert.equal(e.c.juogDisableNegativeAuth04(),false);assert.equal(e.logs.at(-1),'AUTH04_MODE_STATE_UNCONFIRMED_STOP_AND_DISABLE_REQUIRED');assert.equal(e.state().raw.sessionExecutionStage,'AUTH04_APPROVED');assert(!e.logs.join('').includes('SECRET_SENTINEL'))});
test('unknown argument refused before accessing state',()=>{const e=env();assert.equal(e.c.juogAuth04NegativeModeAdmin_('true'),false);assert.equal(e.state().gets,0)});
test('readiness succeeds without any config write',()=>{const e=env(),before=e.state().raw;assert.equal(e.c.juogCheckNegativeAuth04Readiness(),true);assert.equal(e.state().writes,0);assert.deepEqual(e.state().raw,before);const result=JSON.parse(e.logs.at(-1));assert.equal(result.readiness_only,true);assert.equal(result.configuration_changed,false);assert.equal(result.deployment_verified_by_this_function,false);assert.equal(e.state().released,1)});
for(const options of [{badScript:true},{badAcl:true},{badPrincipal:true},{badJournal:true},{config:{sessionExecutionStage:'AUTH04_APPROVED'}},{config:{notificationsDisabled:false}},{lockFail:true}])test('readiness rejects guard drift without any config write',()=>{const e=env(options),before=e.state().raw;assert.equal(e.c.juogCheckNegativeAuth04Readiness(),false);assert.equal(e.state().writes,0);assert.deepEqual(e.state().raw,before)});
test('readiness does not use write availability or create rollback write',()=>{const e=env({alwaysWriteFail:true});assert.equal(e.c.juogCheckNegativeAuth04Readiness(),true);assert.equal(e.state().writes,0)});
test('readonly invalid combinations refused without access',()=>{const e=env();assert.equal(e.c.juogAuth04NegativeModeAdmin_(false,true),false);assert.equal(e.c.juogAuth04NegativeModeAdmin_(true,'true'),false);assert.equal(e.state().gets,0);assert.equal(e.state().writes,0)});

for(const options of [
 {expired:true},{config:{spreadsheetId:'PROTECTED_OTHER'}},{config:{approvedSpreadsheetId:'PROTECTED_OTHER'}},
 {config:{sessionStoreGeneration:'OLD_GENERATION'}},{config:{backupVerified:false}},{config:{fictionalBaselineVerified:false}},
 {config:{qaApproved:false}},{config:{allRoutesReviewed:true}},{config:{schemaParityApproved:true}},
 {aclMutation:a=>a.push(a[1].slice())},{aclMutation:a=>a[1][3]=false},
 {aclMutation:a=>a[1][5]='["TEST01","OTHER"]'},{aclMutation:a=>a[0][0]='wrong'}
])test('additional isolation/ACL prerequisite drift refuses before write',()=>{const e=env(options);assert.equal(e.c.juogEnableNegativeAuth04(),false);assert.equal(e.state().writes,0)});
test('approval reference corresponds to two negative tests',()=>{const e=env();assert.equal(e.c.juogEnableNegativeAuth04(),true);assert.equal(e.state().raw.auth04ExecutionApprovalRef,'PI_EXPLICIT_TWO_NEGATIVE_CORRECTIONS_APPROVAL_20261113')});
test('logs contain no synthetic principal or raw configuration',()=>{const e=env();assert.equal(e.c.juogEnableNegativeAuth04(),true);const logs=e.logs.join('');assert(!logs.includes('SYNTHETIC_OFFLINE_ONLY'));assert(!logs.includes('unchangedSentinel'));assert(!logs.includes('offline-pi'))});
console.log(JSON.stringify({offline_pass:passed,actual_journal_hash_verified:false,synthetic_principal_substitution:true,synthetic_journal_hash_substitution:true,live_requests:0}));


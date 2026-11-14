const fs=require('fs'),vm=require('vm'),crypto=require('crypto'),assert=require('assert/strict');
const root=__dirname+'/../canonical_v9_integration',source=fs.readFileSync(__dirname+'/bundle_recovery_candidate.gs','utf8');
const hash=s=>crypto.createHash('sha256').update(s).digest('hex');
let now=1794614400,locked=false,lockFail=false,writeFail=false,delay=0;
const c={environment:'ISOLATED_TEST',approvalRef:'LOCAL',backupVerified:true,qaApproved:true,fictionalBaselineVerified:true,notificationsDisabled:true,spreadsheetId:'1Hd6EHDPZe8zGcDbILkaBLubgF5atfAzRfpPSN5LemiU',approvedSpreadsheetId:'1Hd6EHDPZe8zGcDbILkaBLubgF5atfAzRfpPSN5LemiU',allRoutesReviewed:true,schemaParityApproved:true,signingKey:'x'.repeat(40),bridgeIssuer:'local',audience:'localgas',oidcIssuer:'https://idp.invalid',resumeDerivationKey:'r'.repeat(40),draftPepper:'p'.repeat(40),sessionPolicy:'isolated_gas_session_b2',sessionStoreGeneration:'synthetic-generation',sessionStoreApproved:true};
c.sessionExecutionStage='AUTH_CONNECT';c.authConnectReviewApproved=true;c.authConnectReviewRef='OFFLINE_REVIEW';c.signingKey=crypto.randomBytes(32).toString('hex');
const hs=new Function(source.slice(source.indexOf('const REGISTRY_HEADERS ='),source.indexOf('function authorizeJuogAction_'))+';return {Registry:REGISTRY_HEADERS,Screening:SCREENING_HEADERS,CRF_Drafts:CRF_DRAFT_HEADERS,MDTReviews:MDT_REVIEW_HEADERS,CRF_30d:CRF_BASE_HEADERS,CRF_90d:CRF_BASE_HEADERS,CRF_Followup:CRF_BASE_HEADERS,CRFSubmissionAudit:CRF_AUDIT_HEADERS};')();
const baseline=Object.fromEntries(Object.entries(hs).map(([k,h])=>[k,[h]]));
const make=(h,o)=>h.map(k=>o[k]??'');baseline.Registry.push(make(hs.Registry,{registration_id:'JUOG-971',status:'ACTIVE',facility_code:'TEST01',registered_at:'2026-03-01',consent_date:'2026-02-28'}));
const raw=JSON.stringify(baseline),journal=[['batch_id','kind','part','total','sha256','data'],['base','baseline',0,1,hash(raw),raw],['base','baseline','SEALED',1,hash(raw),'']];
let events=[['sequence','event_json','chain_sha256']];
const acl=[['issuer','subject','user_id','enabled','role','facility_ids_json','valid_until'],[c.oidcIssuer,'SYNTHETIC','TEST-USER',true,'facility','["TEST01"]','2026-11-19T14:59:00Z']];
const props=new Map([['JUOG_B2_HEAD_'+c.spreadsheetId,'0:'+hash('JUOG-B2|'+c.spreadsheetId+'|synthetic-generation')]]);
const sheet=rows=>({getLastRow:()=>rows.length,getMaxRows:()=>10000,getRange:(start=1,col=1,n=1,width=rows[0].length)=>({getValues:()=>Array.from({length:n},(_,i)=>Array.from({length:width},(_,j)=>rows[start-1+i]?.[col-1+j]??'')),setValues:values=>{if(writeFail)throw Error('INJECTED_IO');values.forEach((r,i)=>{if(rows[start-1+i])throw Error('OVERWRITE_FORBIDDEN');rows[start-1+i]=structuredClone(r)});}}),getDataRange:()=>({getValues:()=>structuredClone(rows)}),appendRow:r=>{if(writeFail)throw Error('INJECTED_IO');rows.push(structuredClone(r));}});
const ss={getSheetByName:n=>n==='D3_Journal'?sheet(journal):n==='V3_Users'?sheet(acl):n==='V3_SessionEvents'&&events?sheet(events):null};
function context(){class Clock extends Date{constructor(...a){super(...(a.length?a:[now*1000]));}static now(){return now*1000;}}
 const x=vm.createContext({ScriptApp:{getScriptId:()=>'11wSp4ePaP5b5A2b5ITZZSZa3YTe-Ex-Tu6oGlEkkRfkPrMCA4deVSZDy'},Date:Clock,PropertiesService:{getScriptProperties:()=>({getProperty:k=>props.get(k),setProperty:(k,v)=>props.set(k,v)})},SpreadsheetApp:{openById:()=>ss,flush:()=>{}},LockService:{getScriptLock:()=>({tryLock:()=>{if(locked||lockFail)return false;locked=true;return true;},releaseLock:()=>locked=false})},Utilities:{getUuid:()=>crypto.randomUUID(),formatDate:()=>new Date(now*1000).toISOString().slice(0,10),Charset:{UTF_8:'utf8'},DigestAlgorithm:{SHA_256:'sha256'},computeDigest:(_,s)=>[...crypto.createHash('sha256').update(s).digest()],computeHmacSha256Signature:(s,k)=>[...crypto.createHmac('sha256',k).update(s).digest()],base64EncodeWebSafe:b=>Buffer.from(b).toString('base64url'),base64DecodeWebSafe:s=>[...Buffer.from(s,'base64url')],newBlob:b=>({getDataAsString:()=>Buffer.from(b).toString('utf8')})}});vm.runInContext(fixtureSource,x);return x;}
const fixtureSource=source.replace('f0ea0ddb132e96bbd08cba4e37dc38609b73db5740530a05225c5acb6cab798f',hash(JSON.stringify(['JUOG-ACL-PROPOSAL-v1',c.oidcIssuer,'SYNTHETIC']))).replace("who.id!=='UAT_TEST01_PI_01'","who.id!=='TEST-USER'");
let x=context(),sid=hash('synthetic-token'),origin=now;
function env(action='ui_context',payload={id:'context',action:'ui_context',payload:{registration_id:''}},changes={}){
 const request_json=JSON.stringify({action,payload}),claims={v:2,iss:c.bridgeIssuer,aud:c.audience,oidc_issuer:c.oidcIssuer,sub:'SYNTHETIC',iat:now,exp:now+15,request_hash:hash(request_json),session:{sid,generation:c.sessionStoreGeneration,jti:crypto.randomUUID().replaceAll('-',''),token_iat:origin,deadline:origin+3600},...changes};
 const encoded=Buffer.from(JSON.stringify(claims)).toString('base64url');return {request_json,identity_assertion:encoded+'.'+crypto.createHmac('sha256',c.signingKey).update(encoded).digest('base64url')};}
const call=e=>x.juogUnifiedIsolationEntryV3_(e,c),checks=[];
function test(name,f){f();checks.push(name);}

assert.equal(hash(source),'ea70e3970a10a405cebdcf6f049ce2f426a91337dadc8846b5a9886b0a382383');

// Only two identity allowlist constants are substituted IN MEMORY for the fictional
// principal. All crypto, ACL, session, request, domain and store functions run intact.
Object.assign(c,{sessionExecutionStage:'AUTH04_APPROVED',b971ExecutionUntil:(now+3600)*1000,auth04ScopeReviewed:true,auth04ScopeReviewRef:'OFFLINE',auth04FixtureProvisioned:true,auth04FixtureManifestSha256:'0bd57252f46b6ac98c1e11d7e7bf983e91ef240ff3c0426c06b9b7bdf0f2e72d',auth04ExecutionApprovalRef:'OFFLINE',canonicalRecoveryReadApproved:true,canonicalRecoveryReviewRef:'OFFLINE',canonicalRecoveryWriteApproved:true,canonicalRecoveryWriteReviewRef:'OFFLINE'});
const q={registration_id:'JUOG-971',facility_code:'TEST01',record_key:'JUOG-971|perioperative_30d|30d'};
const p=JSON.parse(fs.readFileSync(root+'/canonical_fixture.json')).payload;
Object.assign(p,{schema_version:'review-v3-unapproved',submission_id:'OFFLINE-SIGNED-RECOVER',expected_record_version:0,record_key:q.record_key});
let opid,snapshot;
test('recovery read approval alone cannot prepare or execute',()=>{c.canonicalRecoveryWriteApproved=false;assert.equal(call(env('prepare_request',{action:'save_crf',payload:p})).ok,false);assert.equal(call(env('execute_request',{operation_id:'OFFLINE'})).ok,false);c.canonicalRecoveryWriteApproved=true;});
test('recovery read scope excludes other visits',()=>{const bad={...q,record_key:'JUOG-971|day90|90d'};assert.equal(call(env('read_crf',{id:'offline',action:'read_crf',payload:bad})).ok,false)});
test('signed prepare reaches actual request journal',()=>{const r=call(env('prepare_request',{action:'save_crf',payload:p}));assert.equal(r.ok,true,JSON.stringify(r));opid=r.operation_id;snapshot=JSON.stringify(journal);});
test('second pending prepare denied under server lock',()=>{const before=JSON.stringify(journal);const second={...p,submission_id:'OFFLINE-CONCURRENT'};assert.equal(call(env('prepare_request',{action:'save_crf',payload:second})).error,'PENDING_REQUEST_BLOCKS_PREPARE');assert.equal(JSON.stringify(journal),before);});
test('signed recovery reads same actor operation and content digest',()=>{const r=call(env('list_requests',q));assert.equal(r.ok,true,JSON.stringify(r));assert.equal(r.requests.length,1);assert.equal(r.requests[0].operation_id,opid);assert.match(r.requests[0].content_sha256,/^[a-f0-9]{64}$/);assert.equal(JSON.stringify(journal),snapshot);});
test('additional approval false denied',()=>{c.canonicalRecoveryReadApproved=false;assert.equal(call(env('list_requests',q)).error,'AUTH04_SCOPE_DENIED');c.canonicalRecoveryReadApproved=true});
test('other facility request denied',()=>assert.equal(call(env('list_requests',{...q,facility_code:'OTHER'})).ok,false));
test('other case request denied',()=>assert.equal(call(env('list_requests',{...q,registration_id:'JUOG-970'})).ok,false));
test('unregistered principal denied',()=>assert.equal(call(env('list_requests',q,{sub:'UNKNOWN'})).ok,false));
test('registered other principal denied',()=>{acl.push([c.oidcIssuer,'OTHER','OTHER-USER',true,'facility','["TEST01"]','2026-11-19T14:59:00Z']);assert.equal(call(env('list_requests',q,{sub:'OTHER'})).ok,false);acl.pop()});
test('wrong ACL role denied',()=>{acl[1][4]='admin';assert.equal(call(env('list_requests',q)).ok,false);acl[1][4]='facility'});
test('signature tamper denied',()=>{const e=env('list_requests',q);e.identity_assertion=e.identity_assertion.slice(0,-4)+'xxxx';assert.equal(call(e).ok,false)});
test('replay denied',()=>{const e=env('list_requests',q);assert.equal(call(e).ok,true);assert.equal(call(e).error,'ASSERTION_REPLAY')});
test('expired signature denied',()=>{const e=env('list_requests',q);now+=16;assert.equal(call(e).error,'AUTH_EXPIRED')});
test('out of scope API denied',()=>assert.equal(call(env('export_csv',{})).ok,false));
test('AUTH_CONNECT denies route',()=>{c.sessionExecutionStage='AUTH_CONNECT';assert.equal(call(env('list_requests',q)).error,'AUTH04_EXECUTION_NOT_APPROVED');c.sessionExecutionStage='AUTH04_APPROVED'});
test('read recovery did not mutate business journal',()=>assert.equal(JSON.stringify(journal),snapshot));
test('signed execution commits once and recovery confirms saved audit',()=>{
 const r=call(env('execute_request',{operation_id:opid}));assert.equal(r.ok,true,JSON.stringify(r));
 const status=call(env('request_status',{operation_id:opid}));assert.equal(status.state,'SAVED');assert.equal(status.phase,'COMMITTED');
 const saved=JSON.stringify(journal);const discovery=call(env('list_requests',q));assert.equal(discovery.requests[0].state,'SAVED');
 const read=call(env('read_crf',{id:'offline-read',action:'read_crf',payload:q}));assert.equal(read.ok,true,JSON.stringify(read));assert.equal(read.result.records.length,1);assert.equal(read.result.records[0].record_version,1);assert.equal(read.result.records[0].submission_id,p.submission_id);
 const audits=journal.filter(r=>r[1]==='audits'&&r[2]==='SEALED');assert.equal(audits.length,1);assert.equal(JSON.stringify(journal),saved);
});
const out={mode:'OFFLINE_FULL_SIGNED_ENTRY_WITH_TWO_SYNTHETIC_IDENTITY_PIN_SUBSTITUTIONS',source_sha256:hash(source),fixture_source_sha256:hash(fixtureSource),identity_pin_substitutions:2,real_google_authentication:false,live_calls:0,checks,passed:true,count:checks.length,formal_pass_delta:0};fs.writeFileSync(__dirname+'/full_entry_results.json',JSON.stringify(out,null,2)+'\n');console.log(JSON.stringify(out));

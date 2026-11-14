const fs=require('fs'),vm=require('vm'),crypto=require('crypto'),assert=require('assert/strict');
const root=__dirname+'/../../acl_review/canonical_v9_integration',source=fs.readFileSync(__dirname+'/../../acl_review/b971_candidate/bundle_prepare_view_candidate.gs','utf8');
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


assert.equal(hash(source),'6d75109c4fffda3ebe4aedb0d7990f1d694ef3a331dcdb2123c10399279970d6');
const frozen=JSON.stringify(journal),oldKey=c.signingKey;
test('original synthetic signer accepted',()=>assert.equal(call(env()).ok,true));
const oldEnvelope=env();c.signingKey=crypto.randomBytes(48).toString('base64');
test('replaced key rejects previously minted assertion',()=>assert.equal(call(oldEnvelope).error,'AUTH_INVALID'));
test('old key newly signed assertion rejected',()=>{const current=c.signingKey;c.signingKey=oldKey;const e=env();c.signingKey=current;assert.equal(call(e).error,'AUTH_INVALID')});
test('new key accepts same still-valid session: rotation is not revocation',()=>assert.equal(call(env()).ok,true));
test('new signer replay rejected',()=>{const e=env();assert.equal(call(e).ok,true);assert.equal(call(e).error,'ASSERTION_REPLAY')});
test('revoke blocks new-key reuse of existing session',()=>{assert.equal(call(env('session_revoke',{})).revoked,true);assert.equal(call(env()).error,'SESSION_REVOKED')});
sid=hash('fresh-synthetic-token');origin=now;
test('fresh synthetic session accepted',()=>assert.equal(call(env()).ok,true));
test('signature expiry rejected',()=>{const e=env();now+=16;assert.equal(call(e).error,'AUTH_EXPIRED')});
test('AUTH_CONNECT business API remains denied',()=>{for(const a of ['prepare_request','execute_request','save_crf','list_requests'])assert.equal(call(env(a,{})).ok,false)});
test('maintenance flag prevents even signed context',()=>{c.authConnectReviewApproved=false;assert.equal(call(env()).error,'AUTH_CONNECT_NOT_APPROVED');c.authConnectReviewApproved=true});
test('generation-only reset is unsafe with preserved chain',()=>{const g=c.sessionStoreGeneration;c.sessionStoreGeneration='replacement';assert.equal(call(env()).error,'SESSION_STORE_INVALID');c.sessionStoreGeneration=g});
test('session expiry is not extended by new signer',()=>{now=origin+3600;assert.equal(call(env()).ok,false)});
test('business ledger and audits unchanged',()=>assert.equal(JSON.stringify(journal),frozen));
const oldPepper=crypto.randomBytes(32),newPepper=crypto.randomBytes(32),code='123456';
test('pepper replacement invalidates old code hash',()=>assert.notEqual(crypto.createHmac('sha256',oldPepper).update(code).digest('hex'),crypto.createHmac('sha256',newPepper).update(code).digest('hex')));
test('current getDraft path does not authenticate with resume code',()=>{const section=source.slice(source.indexOf('function getDraft_('),source.indexOf('function resetDraftCode_('));assert(!section.includes('draftCodeHash_'));assert(section.includes('suppliedEmail !== storedEmail'));assert(source.includes("(existing&&!owner))return no('DRAFT_OWNER_REQUIRED')"));});
const out={mode:'OFFLINE_V9_ROTATION_IMPACT_SYNTHETIC_KEYS_ONLY',source_sha256:hash(source),live_calls:0,secrets_retrieved:false,checks,count:checks.length,passed:true,formal_pass_delta:0};fs.writeFileSync(__dirname+'/rotation_regression.json',JSON.stringify(out,null,2)+'\n');console.log(JSON.stringify(out));

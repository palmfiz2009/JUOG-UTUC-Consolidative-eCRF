const fs=require('fs'),vm=require('vm'),crypto=require('crypto'),assert=require('assert/strict');const root=__dirname;
const source=fs.readFileSync(root+'/bundle/isolated_review_bundle.gs','utf8');
const hs=new Function(source.slice(source.indexOf('const REGISTRY_HEADERS ='),source.indexOf('function authorizeJuogAction_'))+';return {Registry:REGISTRY_HEADERS,Screening:SCREENING_HEADERS,CRF_Drafts:CRF_DRAFT_HEADERS,MDTReviews:MDT_REVIEW_HEADERS,CRF_30d:CRF_BASE_HEADERS};')();
const make=(h,o)=>h.map(k=>o[k]??'');const baseline=Object.fromEntries(Object.entries(hs).map(([k,v])=>[k,[v]]));
baseline.Registry.push(make(hs.Registry,{registration_id:'JUOG-001',status:'ACTIVE',facility_code:'TEST01',screening_id:'JUOG-SCR-001',best_effect:'SD',cN:'cN1'}));
baseline.Screening.push(make(hs.Screening,{screening_id:'JUOG-SCR-001',status:'REGISTERED',facility_code:'TEST01',registration_id:'JUOG-001',cT:'cT3',cN:'cN1',cM:'cM0'}));
baseline.CRF_Drafts.push(make(hs.CRF_Drafts,{draft_key:'JUOG-001|perioperative_30d|30d',registration_id:'JUOG-001',facility_code:'TEST01',reporter_email:'old@example.invalid',resume_code_hash:'OLD_HASH',draft_json:'{"height":170}'}));

const original=JSON.stringify(baseline),hash=s=>crypto.createHash('sha256').update(s).digest('hex');let fault=false;
const journal=[['batch_id','kind','part','total','sha256','data'],['baseline1','baseline',0,1,hash(original),original],['baseline1','baseline','SEALED',1,hash(original),'']];
const acl=[['issuer','subject','user_id','enabled','role','facility_ids_json','valid_until'],['https://idp.invalid','FICTIONAL-SUB','ADMIN-TEST',true,'admin','["TEST01"]','2026-11-19T14:59:00Z']];
const sheet=rows=>({getRange:()=>({getValues:()=>[rows[0]]}),getDataRange:()=>({getValues:()=>structuredClone(rows)}),appendRow:r=>{if(fault&&r[1]==='audits'){fault=false;throw Error('injected audit failure');}rows.push(structuredClone(r));}});
const ss={getSheetByName:n=>n==='D3_Journal'?sheet(journal):n==='V3_Users'?sheet(acl):null};let locks=0;
const c={environment:'ISOLATED_TEST',approvalRef:'LOCAL-ONLY',backupVerified:true,qaApproved:true,fictionalBaselineVerified:true,notificationsDisabled:true,spreadsheetId:'FICTIONAL-ISOLATION',approvedSpreadsheetId:'FICTIONAL-ISOLATION',voidPolicyApproved:true,signingKey:'LOCAL-SIGN-'+ 'x'.repeat(48),resumeDerivationKey:'LOCAL-RESUME-'+ 'y'.repeat(48),draftPepper:'LOCAL-PEPPER-'+ 'z'.repeat(48),bridgeIssuer:'local',audience:'localgas',oidcIssuer:'https://idp.invalid'};
const ctx=vm.createContext({Date,JSON,Object,Array,String,Number,Error,Math,SpreadsheetApp:{openById:id=>{assert.equal(id,'FICTIONAL-ISOLATION');return ss;},flush:()=>{}},LockService:{getScriptLock:()=>({tryLock:()=>{assert.equal(locks,0);locks++;return true;},releaseLock:()=>locks--})},Utilities:{getUuid:()=>crypto.randomUUID(),Charset:{UTF_8:'utf8'},DigestAlgorithm:{SHA_256:'sha256'},computeDigest:(_,s)=>[...crypto.createHash('sha256').update(s).digest()],computeHmacSha256Signature:(s,k)=>[...crypto.createHmac('sha256',k).update(s).digest()],base64EncodeWebSafe:b=>Buffer.from(b).toString('base64url'),base64DecodeWebSafe:s=>[...Buffer.from(s,'base64url')],newBlob:b=>({getDataAsString:()=>Buffer.from(b).toString('utf8')})}});
vm.runInContext(source,ctx);
const store=()=>ctx.juogDomainSheetsStoreV3_(ss,hash,()=>crypto.randomUUID());
const view=()=>new ctx.JuogDomainServiceV3({store:store(),hash}).readView();
function envelope(op){const request_json=JSON.stringify({action:op.action,payload:op.payload});const now=Math.floor(Date.now()/1000);const claims={v:1,iss:c.bridgeIssuer,aud:c.audience,oidc_issuer:c.oidcIssuer,sub:'FICTIONAL-SUB',iat:now,exp:now+60,request_hash:hash(request_json)};const body=Buffer.from(JSON.stringify(claims)).toString('base64url');return {request_json,identity_assertion:body+'.'+crypto.createHmac('sha256',c.signingKey).update(body).digest('base64url')};}


c.allRoutesReviewed=true;c.schemaParityApproved=true;
acl[1][4]='facility';
const child=require('child_process');
function pythonEnvelope(action,payload){
 const script=`import sys,json,time
from types import SimpleNamespace
sys.path.insert(0,sys.argv[1])
from auth_bridge import signed_request
x=json.load(sys.stdin)
class User(dict):
 is_logged_in=True
u=User(iss=x['issuer'],sub='FICTIONAL-SUB',aud='fixture-client',exp=int(time.time())+300,auth_time=int(time.time()))
cfg=dict(oidc_issuer=x['issuer'],oidc_client_id='fixture-client',max_auth_age_seconds=3600,signing_key=x['key'],bridge_issuer=x['bridge'],audience=x['audience'])
st=SimpleNamespace(user=u,secrets={'juog_identity_bridge':cfg})
print(json.dumps(signed_request(st,x['action'],x['payload'])))`;
 const r=child.spawnSync('python',['-c',script,root+'/python_candidate'],{input:JSON.stringify({issuer:c.oidcIssuer,key:c.signingKey,bridge:c.bridgeIssuer,audience:c.audience,action,payload}),encoding:'utf8'});
 assert.equal(r.status,0,'Synthetic Python signing failed');return JSON.parse(r.stdout);
}
const before=JSON.stringify(journal);
function context(id=''){return pythonEnvelope('ui_context',{id:'context',action:'ui_context',payload:{registration_id:id}});}
let r=ctx.juogUnifiedIsolationEntryV3_(context(),c);assert.equal(r.ok,true);assert.equal(r.facility_code,null);assert.deepEqual(Array.from(r.facilities),['TEST01']);
r=ctx.juogUnifiedIsolationEntryV3_(context('JUOG-001'),c);assert.equal(r.ok,true);assert.equal(r.facility_code,'TEST01');
acl[1][5]='["OTHER"]';r=ctx.juogUnifiedIsolationEntryV3_(context('JUOG-001'),c);assert.equal(r.error,'SUBJECT_FORBIDDEN');
acl[1][5]='["TEST01"]';acl[1][3]=false;r=ctx.juogUnifiedIsolationEntryV3_(context(),c);assert.equal(r.ok,false);acl[1][3]=true;
// Approved administrator identity remains limited to the isolated facility.
acl[1][4]='admin';
r=ctx.juogUnifiedIsolationEntryV3_(context('JUOG-001'),c);assert.equal(r.ok,true);
acl[1][5]='["T1"]';r=ctx.juogUnifiedIsolationEntryV3_(context('JUOG-001'),c);assert.equal(r.error,'SUBJECT_FORBIDDEN');acl[1][5]='["TEST01"]';
const expiry=acl[1][6];acl[1][6]='2000-01-01T00:00:00Z';r=ctx.juogUnifiedIsolationEntryV3_(context(),c);assert.equal(r.ok,false);acl[1][6]=expiry;
acl.push([...acl[1]]);r=ctx.juogUnifiedIsolationEntryV3_(context(),c);assert.equal(r.ok,false);acl.pop();
const subject=acl[1][1];acl[1][1]='UNREGISTERED';r=ctx.juogUnifiedIsolationEntryV3_(context(),c);assert.equal(r.ok,false);acl[1][1]=subject;
const forged=context();forged.request_json+=' ';r=ctx.juogUnifiedIsolationEntryV3_(forged,c);assert.equal(r.error,'REQUEST_SIGNATURE_MISMATCH');
assert.equal(JSON.stringify(journal),before);assert.equal(locks,0);
const result={scope:'Actual Python signed_request -> actual GAS decoder/ACL/ui_context; in-memory Sheets/Utilities/Lock. No live OIDC/GAS/HTTP',checks:['unselected case facility list','own case context','foreign facility denied','revoked principal denied','tampered signed request denied','journal byte-for-byte unchanged','lock released','TEST01 admin context','T1 mismatch denied','expired ACL denied','duplicate ACL denied','unregistered subject denied'],result:'PASS',formal_uat_changed:false};
fs.writeFileSync(root+'/../uat_evidence/test01_python_gas_context_results.json',JSON.stringify(result,null,2));console.log(JSON.stringify(result));

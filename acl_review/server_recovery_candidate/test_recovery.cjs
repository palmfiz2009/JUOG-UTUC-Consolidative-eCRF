const fs=require('fs'),assert=require('assert/strict');
const s=fs.readFileSync(__dirname+'/bundle_recovery_candidate.gs','utf8');
const x=new Function(s+';return {juogCanonicalRecoveryList_,juogCanonicalRecoveryScope_,juogAuth04Request_};')();
const p={registration_id:'JUOG-971',facility_code:'TEST01',record_key:'JUOG-971|perioperative_30d|30d'},who={id:'offline',enabled:true,role:'facility',facilities:['TEST01']},cfg={sessionExecutionStage:'AUTH04_APPROVED',canonicalRecoveryReadApproved:true,canonicalRecoveryReviewRef:'OFFLINE'};
const row=(id,actor='offline',caseId='JUOG-971')=>({id,actor,operation:{action:'save_crf',payload:{...p,registration_id:caseId,crf_type:'perioperative_30d',visit:'30d',submission_id:'submission',expected_record_version:2,data:{private:'NEVER_RETURN'}}}});
let requests=[row('observed-id'),row('other-user','other'),row('other-case','offline','JUOG-970')],statuses={};const store={read:()=>({requests})},service={readView:()=>({tables:{}}),authorize:()=>({ok:true})},life={status:id=>statuses[id]||{ok:true,operation_id:id,action:'save_crf',state:'UNFINISHED',phase:'PREPARED'}};
const run=(c=cfg,u=who,q=p)=>x.juogCanonicalRecoveryList_(store,service,life,u,q,c),checks=[];function test(n,f){f();checks.push(n)}
test('recover same server operation after client memory loss',()=>{const a=run(),b=run();assert.equal(a.requests.length,1);assert.equal(a.requests[0].operation_id,b.requests[0].operation_id);assert.equal(a.read_only,true);assert(!JSON.stringify(a).includes('NEVER_RETURN'));assert(!JSON.stringify(a).includes('offline'))});
test('AUTH_CONNECT rejects route',()=>assert.equal(run({...cfg,sessionExecutionStage:'AUTH_CONNECT'}).error,'RECOVERY_READ_NOT_APPROVED'));
test('unapproved route rejected',()=>assert.equal(run({...cfg,canonicalRecoveryReadApproved:false}).ok,false));
test('wrong role facility or disabled denied',()=>{for(const u of [{...who,role:'admin'},{...who,facilities:['OTHER']},{...who,enabled:false}])assert.equal(run(cfg,u).ok,false)});
test('scope extras and other record rejected',()=>{for(const q of [{...p,secret:'NEVER_RETURN'},{...p,record_key:'JUOG-970|perioperative_30d|30d'}])assert.equal(run(cfg,who,q).ok,false)});
test('unknown status fails closed',()=>{statuses['observed-id']={ok:false};assert.equal(run().ok,false);statuses={}});
test('business journal never mutated',()=>{const before=JSON.stringify(requests);run();assert.equal(JSON.stringify(requests),before)});
test('request gate accepts only exact scoped recovery',()=>{x.juogAuth04Request_({action:'list_requests',payload:p});assert.throws(()=>x.juogAuth04Request_({action:'list_requests',payload:{}}))});
test('malformed metadata cannot leak through summaries',()=>{for(const change of [{submission_id:{secret:'NEVER_RETURN'}},{submission_id:'x'.repeat(500)},{expected_record_version:-1},{crf_type:'day90'}]){const before=requests;requests=[row('observed-id')];Object.assign(requests[0].operation.payload,change);const result=run();assert.equal(result.ok,false);assert(!JSON.stringify(result).includes('NEVER_RETURN'));requests=before}});
const out={mode:'OFFLINE_CANDIDATE_READONLY_RECOVERY_NOT_DEPLOYED',checks,passed:true,count:checks.length,live_business_calls:0};fs.writeFileSync(__dirname+'/results.json',JSON.stringify(out,null,2)+'\n');console.log(JSON.stringify(out));

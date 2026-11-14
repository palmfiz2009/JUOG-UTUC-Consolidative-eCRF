/* Independent, entirely offline tests. All credential strings are synthetic. */
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const SCRIPT='11wSp4ePaP5b5A2b5ITZZSZa3YTe-Ex-Tu6oGlEkkRfkPrMCA4deVSZDy',SHEET='1Hd6EHDPZe8zGcDbILkaBLubgF5atfAzRfpPSN5LemiU';
const base={environment:'ISOLATED_TEST',approvalRef:'synthetic',backupVerified:true,qaApproved:true,fictionalBaselineVerified:true,notificationsDisabled:true,spreadsheetId:SHEET,approvedSpreadsheetId:SHEET,sessionPolicy:'isolated_gas_session_b2',sessionExecutionStage:'AUTH_CONNECT',authConnectReviewApproved:true,authConnectReviewRef:'synthetic',allRoutesReviewed:false,schemaParityApproved:false};
const syntheticKeys={ADMIN_BRIDGE_SIGNING_KEY:'synthetic-signing',ADMIN_RESUME_DERIVATION_KEY:'synthetic-resume',ADMIN_DRAFT_PEPPER:'synthetic-pepper'};
function fixture(source,options={}){
 let raw=JSON.stringify(base),keys={...syntheticKeys},locked=false,released=0,decoded=0,session=0,opened=0,propertyReads=0;
 const snapshot={...base,signingKey:keys.ADMIN_BRIDGE_SIGNING_KEY,resumeDerivationKey:keys.ADMIN_RESUME_DERIVATION_KEY,draftPepper:keys.ADMIN_DRAFT_PEPPER};
 const ctx={ScriptApp:{getScriptId:()=>SCRIPT},LockService:{getScriptLock:()=>({tryLock:()=>{if(options.busy)return false;locked=true;options.onLock?.({setRaw:r=>raw=r,keys});return true;},releaseLock:()=>{assert.equal(locked,true);locked=false;released++;}})},PropertiesService:{getScriptProperties:()=>({getProperty(k){assert.equal(locked,true,'runtime reads must be inside lock');propertyReads++;if(options.readError)throw Error('synthetic private detail');if(k==='UNIFIED_ISOLATION_CONFIG')return raw;assert.ok(k in syntheticKeys);return keys[k];}})},juogV3DecodeBridge_:()=>{assert.equal(locked,true);decoded++;options.afterGuard?.({setRaw:r=>raw=r,keys});return {request:{action:'ui_context',payload:{action:'ui_context',payload:{}}},principal:{issuer:'synthetic',subject:'synthetic'}};},SpreadsheetApp:{openById:()=>{opened++;return {}; }},juogV3ReadIndividualAcl_:()=>({role:'facility',id:'synthetic',enabled:true,facilities:['TEST01']}),juogSessionGateB2_:()=>{session++;return {guard:()=>assert.equal(locked,true)};},juogDomainSheetsStoreV3_:()=>{throw Error('business store must not be constructed');},console:{info:()=>{throw Error('unexpected log');}}};
 vm.createContext(ctx);
 const entry=source.slice(source.indexOf('function juogUnifiedIsolationEntryV3_('),source.indexOf('// SOURCE: isolation_unified_webapp.gs'));
 const helper=source.slice(source.indexOf('function juogRequireCurrentRuntimeSnapshot_('));
 vm.runInContext(entry+'\n'+helper,ctx);
 return {snapshot,run:()=>ctx.juogUnifiedIsolationEntryV3_({},snapshot),get counts(){return {released,decoded,session,opened,propertyReads};}};
}
let total=0;
function test(label,f){f();total++;console.log('PASS '+label);}
for(const name of ['version9','recovery']){
 const source=fs.readFileSync(__dirname+'/'+name+'_candidate.gs','utf8');
 new vm.Script(source);
 test(name+': matching locked snapshot reaches auth-only branch',()=>{const f=fixture(source);assert.equal(f.run().ok,true);assert.deepEqual(f.counts,{released:1,decoded:1,session:1,opened:1,propertyReads:4});});
 for(const [label,change] of [
 ['disabled gate',x=>x.setRaw(JSON.stringify({...base,authConnectReviewApproved:false}))],
 ['changed stage',x=>x.setRaw(JSON.stringify({...base,sessionExecutionStage:'AUTH04_APPROVED'}))],
 ['unrelated config field',x=>x.setRaw(JSON.stringify({...base,unrelated:'changed'}))],
 ['missing config',x=>x.setRaw(null)],['malformed JSON',x=>x.setRaw('{')],['null config',x=>x.setRaw('null')],
 ...Object.keys(syntheticKeys).map(k=>['rotation '+k,x=>{x.keys[k]='synthetic-rotated';}]),
 ])test(name+': rejects '+label+' before decode/session/access',()=>{const f=fixture(source,{onLock:change}),r=f.run();assert.equal(r.error,'CONFIGURATION_CHANGED');assert.equal(r.ok,false);assert.equal(f.counts.released,1);assert.equal(f.counts.decoded,0);assert.equal(f.counts.session,0);assert.equal(f.counts.opened,0);});
 test(name+': JSON member reorder preserves equality',()=>{const f=fixture(source,{onLock:x=>x.setRaw(JSON.stringify(Object.fromEntries(Object.entries(base).reverse())))});assert.equal(f.run().ok,true);});
 test(name+': nested object reorder preserves equality',()=>{const f=fixture(source,{onLock:x=>x.setRaw(JSON.stringify({...base,extra:{z:3,a:{b:2,a:1}}}))});f.snapshot.extra={a:{a:1,b:2},z:3};assert.equal(f.run().ok,true);});
 test(name+': array reorder is a material change',()=>{const f=fixture(source,{onLock:x=>x.setRaw(JSON.stringify({...base,extra:['b','a']}))});f.snapshot.extra=['a','b'];assert.equal(f.run().error,'CONFIGURATION_CHANGED');assert.equal(f.counts.decoded,0);});
 test(name+': numeric/string type change is material',()=>{const f=fixture(source,{onLock:x=>x.setRaw(JSON.stringify({...base,extra:'1'}))});f.snapshot.extra=1;assert.equal(f.run().error,'CONFIGURATION_CHANGED');assert.equal(f.counts.decoded,0);});
 test(name+': null/missing field change is material',()=>{const f=fixture(source);f.snapshot.extra=null;assert.equal(f.run().error,'CONFIGURATION_CHANGED');assert.equal(f.counts.decoded,0);});
 test(name+': property read error produces only fixed safe reason',()=>{const f=fixture(source,{readError:true}),r=f.run();assert.equal(JSON.stringify(r),' {"ok":false,"error":"CONFIGURATION_CHANGED"}'.trim());assert.equal(f.counts.decoded,0);assert.equal(f.counts.released,1);});
 test(name+': failed lock does not read properties or decode',()=>{const f=fixture(source,{busy:true});assert.equal(f.run().error,'LOCK_TIMEOUT');assert.deepEqual(f.counts,{released:0,decoded:0,session:0,opened:0,propertyReads:0});});
 test(name+': LIMITATION noncooperating change after check is not detected',()=>{const f=fixture(source,{afterGuard:x=>x.setRaw(JSON.stringify({...base,authConnectReviewApproved:false}))});assert.equal(f.run().ok,true);});
}
console.log(`${total} independent offline tests passed; limitation case intentionally demonstrates boundary.`);

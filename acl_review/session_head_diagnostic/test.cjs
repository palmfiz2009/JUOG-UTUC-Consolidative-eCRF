const fs=require('fs'),vm=require('vm'),crypto=require('crypto'),assert=require('assert');
const source=fs.readFileSync(__dirname+'/diagnostic.gs','utf8');
const sheet='1Hd6EHDPZe8zGcDbILkaBLubgF5atfAzRfpPSN5LemiU',gen='d72bcf33-423d-4c4d-862d-2e2d69bc3edf';
const hash=s=>crypto.createHash('sha256').update(s).digest('hex');
function run(mode){
 const c={environment:'ISOLATED_TEST',spreadsheetId:sheet,approvedSpreadsheetId:sheet,sessionExecutionStage:'AUTH_CONNECT',authConnectReviewApproved:false,sessionStoreGeneration:gen,sessionPolicy:'isolated_gas_session_b2',sessionStoreApproved:true};
 let chain=hash('JUOG-B2|'+sheet+'|'+gen);const heads=[chain],rows=[['sequence','event_json','chain_sha256']];
 for(let i=1;i<=2;i++){const e={kind:i===1?'OPEN':'USE',sid:'a'.repeat(64),owner:'b'.repeat(64),deadline:123456,jti:i===1?'':'synthetic-jti'};if(mode==='duplicate')e.kind='OPEN';const json=JSON.stringify(e);chain=hash(chain+'|'+i+'|'+json);rows.push([i,json,chain]);heads.push(chain);}
 let head='2:'+chain;
 if(mode==='behind')head='1:'+heads[1];if(mode==='wrong')head='1:'+'c'.repeat(64);if(mode==='ahead')head='3:'+chain;
 if(mode==='badchain')rows[2][2]='d'.repeat(64);if(mode==='badjson')rows[1][1]='bad';
 if(mode==='active')c.authConnectReviewApproved=true;if(mode==='generation')c.sessionStoreGeneration='wrong';if(mode==='target')c.spreadsheetId='wrong';
 const log=[],keys=[];let unlock=0;
 const ctx={ScriptApp:{getScriptId:()=> '11wSp4ePaP5b5A2b5ITZZSZa3YTe-Ex-Tu6oGlEkkRfkPrMCA4deVSZDy'},LockService:{getScriptLock:()=>({tryLock:()=>mode!=='busy',releaseLock:()=>unlock++})},PropertiesService:{getScriptProperties:()=>({getProperty:k=>{keys.push(k);if(k==='UNIFIED_ISOLATION_CONFIG')return JSON.stringify(c);if(k==='JUOG_B2_HEAD_'+sheet)return head;throw Error('SECRET_ACCESS');}})},SpreadsheetApp:{openById:id=>{assert.equal(id,sheet);if(mode==='exception')throw Error('PRIVATE_EXCEPTION_SENTINEL');return {getSheetByName:()=>({getDataRange:()=>({getValues:()=>rows})})};}},Utilities:{DigestAlgorithm:{SHA_256:'sha256'},Charset:{UTF_8:'utf8'},computeDigest:(_,s)=>[...crypto.createHash('sha256').update(s).digest()]},console:{info:x=>log.push(x)}};
 vm.createContext(ctx);vm.runInContext(source,ctx);const out=ctx.juogReadOnlySessionHeadDiagnostic();
 assert.equal(log.length,1);for(const marker of ['a'.repeat(64),'b'.repeat(64),'synthetic-jti','PRIVATE_EXCEPTION_SENTINEL'])assert(!log[0].includes(marker));
 assert(keys.every(k=>k==='UNIFIED_ISOLATION_CONFIG'||k==='JUOG_B2_HEAD_'+sheet));assert.equal(unlock,mode==='busy'?0:1);return out;
}
const cases={normal:'MATCH',behind:'HEAD_BEHIND_VALID_CHAIN',wrong:'HEAD_MISMATCH',ahead:'HEAD_MISMATCH',badchain:'CHAIN_INVALID',badjson:'CHAIN_INVALID',duplicate:'DUPLICATE_OPEN',active:'STOP_NOT_CONFIRMED',generation:'SESSION_CONFIG_MISMATCH',target:'TARGET_MISMATCH',busy:'BUSY',exception:'READ_FAILED'};
for(const [mode,want] of Object.entries(cases))assert.equal(run(mode).result,want,mode);
assert(!/setProperty|setProperties|appendRow|setValue|UrlFetch|MailApp|getProperties\(/.test(source));
console.log(JSON.stringify({passed:Object.keys(cases).length,network:false,mutations:false,secret_property_reads:false,scope:'offline diagnostic tests, not live UAT'}));

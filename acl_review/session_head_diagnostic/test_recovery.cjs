const fs=require('fs'),vm=require('vm'),crypto=require('crypto'),assert=require('assert');
const source=fs.readFileSync(__dirname+'/recovery_candidate.gs','utf8');
const hash=s=>crypto.createHash('sha256').update(s).digest('hex');
const sheet='1Hd6EHDPZe8zGcDbILkaBLubgF5atfAzRfpPSN5LemiU',gen='d72bcf33-423d-4c4d-862d-2e2d69bc3edf';
function run(mode){
 let chain=hash('JUOG-B2|'+sheet+'|'+gen),heads=[chain],rows=[['sequence','event_json','chain_sha256']];
 for(let i=1;i<=362;i++){let json=JSON.stringify({kind:i===1?'OPEN':'USE',sid:'a'.repeat(64),owner:'b'.repeat(64),deadline:100,jti:i===1?'':'j'+i});chain=hash(chain+'|'+i+'|'+json);rows.push([i,json,chain]);heads.push(chain);}
 const journal=Array.from({length:165},()=>['synthetic','','','','','']);
 let s=source.replace(/const PIN360='[^']+'/,"const PIN360='"+heads[360]+"'").replace(/const PIN362='[^']+'/,"const PIN362='"+heads[362]+"'").replace('1414934e5e059e3cc7882486fa7cf5ee14afe99b4ab5dce9736a3c665d0b0797',hash(JSON.stringify(journal)));
 const c={environment:'ISOLATED_TEST',spreadsheetId:sheet,approvedSpreadsheetId:sheet,sessionExecutionStage:'AUTH_CONNECT',authConnectReviewApproved:false,sessionStoreGeneration:gen,sessionPolicy:'isolated_gas_session_b2',sessionStoreApproved:true};
 let head='360:'+heads[360],writes=0,reads=0,configReads=0,sheetReads=0;const logs=[];
 if(mode==='active')c.authConnectReviewApproved=true;
 if(mode==='changed')rows[362][2]='c'.repeat(64);
 if(mode==='journal')journal[0][0]='changed';
 if(mode==='wronghead')head='359:'+heads[359];
 if(mode==='pin')s=s.replace(heads[362],'d'.repeat(64));
 const ctx={Date:{now:()=>mode==='live'?99000:100000},ScriptApp:{getScriptId:()=> '11wSp4ePaP5b5A2b5ITZZSZa3YTe-Ex-Tu6oGlEkkRfkPrMCA4deVSZDy'},LockService:{getScriptLock:()=>({tryLock:()=>true,releaseLock:()=>{}})},PropertiesService:{getScriptProperties:()=>({getProperty:k=>{if(k==='UNIFIED_ISOLATION_CONFIG'){configReads++;if(mode==='config_race'&&configReads>1)c.authConnectReviewApproved=true;if(mode==='post_config_race'&&writes)c.authConnectReviewApproved=true;return JSON.stringify(c);}assert.equal(k,'JUOG_B2_HEAD_'+sheet);reads++;return mode==='concurrent'&&reads>1?'unexpected':head;},setProperty:(k,v)=>{assert.equal(k,'JUOG_B2_HEAD_'+sheet);writes++;if(mode==='uncertain')throw Error('private');head=v;}})},SpreadsheetApp:{openById:()=>({getSheetByName:n=>({getDataRange:()=>({getValues:()=>{sheetReads++;const data=JSON.parse(JSON.stringify(n==='D3_Journal'?journal:rows));if(mode==='ledger_race'&&n!=='D3_Journal'&&sheetReads>2)data[1][1]='changed';return data;}})})})},Utilities:{DigestAlgorithm:{SHA_256:'sha256'},Charset:{UTF_8:'utf8'},computeDigest:(_,s)=>[...crypto.createHash('sha256').update(s).digest()]},console:{info:s=>logs.push(s)}};
 vm.createContext(ctx);vm.runInContext(s,ctx);
 const result=ctx.juogRecoverExpiredSessionHead(mode!=='dry',mode==='noapproval'?'':'PI_SESSION_HEAD_REPAIR_360_362');
 assert.equal(logs.length,1);assert(!logs[0].includes('a'.repeat(64)));assert.equal(c.authConnectReviewApproved,['active','config_race','post_config_race'].includes(mode));
 assert.equal(writes,['apply','uncertain','post_config_race'].includes(mode)?1:0);
 if(mode==='apply')assert.equal(head,'362:'+heads[362]);return result.result;
}
const cases={config_race:'CONCURRENT_CHANGE',ledger_race:'CONCURRENT_CHANGE',post_config_race:'WRITE_UNCERTAIN_KEEP_STOPPED',dry:'DRY_RUN_READY',apply:'HEAD_REPAIRED_AUTH_REMAINS_DISABLED',live:'UNEXPIRED_SESSIONS',active:'STOP_NOT_CONFIRMED',changed:'CHAIN_INVALID',journal:'BUSINESS_BASELINE_CHANGED',wronghead:'UNEXPECTED_STATE',pin:'SNAPSHOT_CHANGED',concurrent:'CONCURRENT_CHANGE',noapproval:'REPAIR_APPROVAL_REQUIRED',uncertain:'WRITE_UNCERTAIN_KEEP_STOPPED'};
for(const [mode,want] of Object.entries(cases))assert.equal(run(mode),want,mode);
console.log(JSON.stringify({passed:Object.keys(cases).length,scope:'synthetic offline recovery tests',liveRepair:false}));

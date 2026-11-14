// UNDEPLOYED recovery candidate. Default dry-run. Never enables authentication.
function juogRecoverExpiredSessionHead(execute, approvalRef) {
 const PIN360='1f7e38184f17b61a4330a8fe57d7ef3999107c77bc6ed49598ca801cc480aed3';
 const PIN362='76078305b5c16b042b0b9d03394a4c4a88bd571efe1a44ea34495e16f343b33d';
 const script='11wSp4ePaP5b5A2b5ITZZSZa3YTe-Ex-Tu6oGlEkkRfkPrMCA4deVSZDy';
 const sheet='1Hd6EHDPZe8zGcDbILkaBLubgF5atfAzRfpPSN5LemiU';
 const generation='d72bcf33-423d-4c4d-862d-2e2d69bc3edf';
 const out={diagnostic:'SESSION_HEAD_RECOVERY_CANDIDATE_V1',ok:false};
 let locked=false,lock,writeAttempted=false;
 try {
  if(ScriptApp.getScriptId()!==script)throw Error('TARGET_MISMATCH');
  lock=LockService.getScriptLock();locked=lock.tryLock(1000);
  if(!locked)throw Error('BUSY');
  const p=PropertiesService.getScriptProperties();
  const configRaw=p.getProperty('UNIFIED_ISOLATION_CONFIG');
  const c=JSON.parse(configRaw);
  if(!c||c.environment!=='ISOLATED_TEST'||c.spreadsheetId!==sheet||c.approvedSpreadsheetId!==sheet)throw Error('TARGET_MISMATCH');
  if(c.sessionExecutionStage!=='AUTH_CONNECT'||c.authConnectReviewApproved!==false)throw Error('STOP_NOT_CONFIRMED');
  if(c.sessionStoreGeneration!==generation||c.sessionPolicy!=='isolated_gas_session_b2'||c.sessionStoreApproved!==true)throw Error('SESSION_CONFIG_MISMATCH');
  const sh=SpreadsheetApp.openById(sheet).getSheetByName('V3_SessionEvents');
  if(!sh)throw Error('SHEET_MISSING');
  const rows=sh.getDataRange().getValues();
  if(rows.length>10001||JSON.stringify(rows[0])!==JSON.stringify(['sequence','event_json','chain_sha256']))throw Error('STRUCTURE_INVALID');
  const hash=s=>Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256,s,Utilities.Charset.UTF_8).map(b=>('0'+((b+256)%256).toString(16)).slice(-2)).join('');
  let chain=hash('JUOG-B2|'+sheet+'|'+generation);
  const heads=[chain],opens=new Set(); let maxDeadline=0;
  for(let i=1;i<rows.length;i++){
   const r=rows[i];
   if(r.length!==3||r[0]!==i||typeof r[1]!=='string')throw Error('STRUCTURE_INVALID');
   chain=hash(chain+'|'+i+'|'+r[1]);
   if(chain!==r[2])throw Error('CHAIN_INVALID');
   const e=JSON.parse(r[1]);
   if(!e||!['OPEN','USE','REVOKE'].includes(e.kind)||!/^[a-f0-9]{64}$/.test(e.sid)||!/^[a-f0-9]{64}$/.test(e.owner)||!Number.isInteger(e.deadline)||typeof e.jti!=='string')throw Error('EVENT_INVALID');
   maxDeadline=Math.max(maxDeadline,e.deadline);
   if(e.kind==='OPEN'){if(opens.has(e.sid))throw Error('DUPLICATE_OPEN');opens.add(e.sid);}
   heads.push(chain);
  }
  const raw=p.getProperty('JUOG_B2_HEAD_'+sheet);
  const m=/^(0|[1-9][0-9]*):([a-f0-9]{64})$/.exec(raw||'');
  if(!m)throw Error('HEAD_FORMAT_INVALID');
  const n=Number(m[1]);if(!Number.isSafeInteger(n))throw Error('HEAD_FORMAT_INVALID');
  out.events=rows.length-1;out.headSequence=n;
  out.headMatchesHistoricalRow=n<heads.length&&m[2]===heads[n];
  out.headMatchesCurrent=n===out.events&&out.headMatchesHistoricalRow;
  if(rows.length!==363||n!==360||!out.headMatchesHistoricalRow)throw Error('UNEXPECTED_STATE');
  if(heads[360]!==PIN360||chain!==PIN362)throw Error('SNAPSHOT_CHANGED');
  if(Math.floor(Date.now()/1000)<maxDeadline)throw Error('UNEXPIRED_SESSIONS');
  const journal=SpreadsheetApp.openById(sheet).getSheetByName('D3_Journal').getDataRange().getValues();
  if(journal.length!==165||journal.some(r=>r.length!==6)||hash(JSON.stringify(journal))!=='1414934e5e059e3cc7882486fa7cf5ee14afe99b4ab5dce9736a3c665d0b0797')throw Error('BUSINESS_BASELINE_CHANGED');
  function verifyUnchanged(){
   if(p.getProperty('UNIFIED_ISOLATION_CONFIG')!==configRaw||JSON.stringify(sh.getDataRange().getValues())!==JSON.stringify(rows)||JSON.stringify(SpreadsheetApp.openById(sheet).getSheetByName('D3_Journal').getDataRange().getValues())!==JSON.stringify(journal))throw Error('CONCURRENT_CHANGE');
  }
  verifyUnchanged();
  if(p.getProperty('JUOG_B2_HEAD_'+sheet)!==raw)throw Error('CONCURRENT_CHANGE');
  if(execute!==true){out.ok=true;out.result='DRY_RUN_READY';}else{
  if(approvalRef!=='PI_SESSION_HEAD_REPAIR_360_362')throw Error('REPAIR_APPROVAL_REQUIRED');
  // Only one non-secret consistency pointer changes. No ledger, key, generation or gate mutation.
  writeAttempted=true;
  p.setProperty('JUOG_B2_HEAD_'+sheet,'362:'+chain);
  if(p.getProperty('JUOG_B2_HEAD_'+sheet)!=='362:'+chain)throw Error('WRITE_UNCERTAIN_KEEP_STOPPED');
  verifyUnchanged();
  out.ok=true;out.result='HEAD_REPAIRED_AUTH_REMAINS_DISABLED';}
 }catch(e){
  const safe=['UNEXPECTED_STATE','SNAPSHOT_CHANGED','UNEXPIRED_SESSIONS','BUSINESS_BASELINE_CHANGED','CONCURRENT_CHANGE','REPAIR_APPROVAL_REQUIRED','WRITE_UNCERTAIN_KEEP_STOPPED','TARGET_MISMATCH','BUSY','STOP_NOT_CONFIRMED','SESSION_CONFIG_MISMATCH','SHEET_MISSING','STRUCTURE_INVALID','CHAIN_INVALID','EVENT_INVALID','DUPLICATE_OPEN','HEAD_FORMAT_INVALID'];
  out.result=writeAttempted?'WRITE_UNCERTAIN_KEEP_STOPPED':safe.includes(e.message)?e.message:'READ_FAILED';
 }finally{if(locked)lock.releaseLock();}
 console.info(JSON.stringify(out));return out;
}

// Administrator editor-only diagnostic. No deployment, mutation, or secret read.
function juogReadOnlySessionHeadDiagnostic() {
 const script='11wSp4ePaP5b5A2b5ITZZSZa3YTe-Ex-Tu6oGlEkkRfkPrMCA4deVSZDy';
 const sheet='1Hd6EHDPZe8zGcDbILkaBLubgF5atfAzRfpPSN5LemiU';
 const generation='d72bcf33-423d-4c4d-862d-2e2d69bc3edf';
 const out={diagnostic:'SESSION_HEAD_READONLY_V1',ok:false};
 let locked=false,lock;
 try {
  if(ScriptApp.getScriptId()!==script)throw Error('TARGET_MISMATCH');
  lock=LockService.getScriptLock();locked=lock.tryLock(1000);
  if(!locked)throw Error('BUSY');
  const p=PropertiesService.getScriptProperties();
  const c=JSON.parse(p.getProperty('UNIFIED_ISOLATION_CONFIG'));
  if(!c||c.environment!=='ISOLATED_TEST'||c.spreadsheetId!==sheet||c.approvedSpreadsheetId!==sheet)throw Error('TARGET_MISMATCH');
  if(c.sessionExecutionStage!=='AUTH_CONNECT'||c.authConnectReviewApproved!==false)throw Error('STOP_NOT_CONFIRMED');
  if(c.sessionStoreGeneration!==generation||c.sessionPolicy!=='isolated_gas_session_b2'||c.sessionStoreApproved!==true)throw Error('SESSION_CONFIG_MISMATCH');
  const sh=SpreadsheetApp.openById(sheet).getSheetByName('V3_SessionEvents');
  if(!sh)throw Error('SHEET_MISSING');
  const rows=sh.getDataRange().getValues();
  if(rows.length>10001||JSON.stringify(rows[0])!==JSON.stringify(['sequence','event_json','chain_sha256']))throw Error('STRUCTURE_INVALID');
  const hash=s=>Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256,s,Utilities.Charset.UTF_8).map(b=>('0'+((b+256)%256).toString(16)).slice(-2)).join('');
  let chain=hash('JUOG-B2|'+sheet+'|'+generation);
  const heads=[chain],opens=new Set();
  for(let i=1;i<rows.length;i++){
   const r=rows[i];
   if(r.length!==3||r[0]!==i||typeof r[1]!=='string')throw Error('STRUCTURE_INVALID');
   chain=hash(chain+'|'+i+'|'+r[1]);
   if(chain!==r[2])throw Error('CHAIN_INVALID');
   const e=JSON.parse(r[1]);
   if(!e||!['OPEN','USE','REVOKE'].includes(e.kind)||!/^[a-f0-9]{64}$/.test(e.sid)||!/^[a-f0-9]{64}$/.test(e.owner)||!Number.isInteger(e.deadline)||typeof e.jti!=='string')throw Error('EVENT_INVALID');
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
  out.ok=true;out.result=out.headMatchesCurrent?'MATCH':out.headMatchesHistoricalRow?'HEAD_BEHIND_VALID_CHAIN':'HEAD_MISMATCH';
 }catch(e){
  const safe=['TARGET_MISMATCH','BUSY','STOP_NOT_CONFIRMED','SESSION_CONFIG_MISMATCH','SHEET_MISSING','STRUCTURE_INVALID','CHAIN_INVALID','EVENT_INVALID','DUPLICATE_OPEN','HEAD_FORMAT_INVALID'];
  out.result=safe.includes(e.message)?e.message:'READ_FAILED';
 }finally{if(locked)lock.releaseLock();}
 console.info(JSON.stringify(out));return out;
}

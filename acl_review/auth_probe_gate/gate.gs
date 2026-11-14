// Editor-only helper. No deployment, credential reads, or business mutations.
// PI authorized one normal OIDC/ui_context probe, followed by disable regardless of outcome.
function juogAuthProbeGate_(enable) {
 const sid='11wSp4ePaP5b5A2b5ITZZSZa3YTe-Ex-Tu6oGlEkkRfkPrMCA4deVSZDy';
 const sheet='1Hd6EHDPZe8zGcDbILkaBLubgF5atfAzRfpPSN5LemiU';
 const out={check:'AUTH_PROBE_GATE_V1',ok:false};
 let lock,locked=false,p,c,attempted=false;
 try {
  if(ScriptApp.getScriptId()!==sid)throw Error('TARGET');
  lock=LockService.getScriptLock();locked=lock.tryLock(1000);if(!locked)throw Error('BUSY');
  p=PropertiesService.getScriptProperties();
  const raw=p.getProperty('UNIFIED_ISOLATION_CONFIG');c=JSON.parse(raw);
  if(!c||c.environment!=='ISOLATED_TEST'||c.spreadsheetId!==sheet||c.approvedSpreadsheetId!==sheet||c.sessionExecutionStage!=='AUTH_CONNECT')throw Error('TARGET');
  if(enable===true){
   if(c.authConnectReviewApproved!==false||c.sessionPolicy!=='isolated_gas_session_b2'||c.sessionStoreApproved!==true||c.sessionStoreGeneration!=='d72bcf33-423d-4c4d-862d-2e2d69bc3edf')throw Error('CONFIG');
   if(c.allRoutesReviewed!==false||c.schemaParityApproved!==false||c.auth04ScopeReviewed!==false||c.auth04FixtureProvisioned!==false||c.auth04ExecutionApprovalRef!==null)throw Error('BUSINESS_GUARD');
   if(c.notificationsDisabled!==true||c.backupVerified!==true||c.qaApproved!==true||c.fictionalBaselineVerified!==true||typeof c.authConnectReviewRef!=='string'||!c.authConnectReviewRef.trim())throw Error('REVIEW');
   const ss=SpreadsheetApp.openById(sheet),store=juogSessionStoreB2_(ss,c);
   out.sessionEvents=store.read().events.length;
   const rows=ss.getSheetByName('D3_Journal').getDataRange().getValues();
   if(rows.length!==165||rows.some(r=>r.length!==6)||store.hash(JSON.stringify(rows))!=='1414934e5e059e3cc7882486fa7cf5ee14afe99b4ab5dce9736a3c665d0b0797')throw Error('BASELINE');
  }else if(enable!==false)throw Error('ARGUMENT');
  if(p.getProperty('UNIFIED_ISOLATION_CONFIG')!==raw)throw Error('CONCURRENT');
  c.authConnectReviewApproved=enable;
  const next=JSON.stringify(c);attempted=true;p.setProperty('UNIFIED_ISOLATION_CONFIG',next);
  if(p.getProperty('UNIFIED_ISOLATION_CONFIG')!==next)throw Error('UNCERTAIN');
  out.ok=true;out.authEnabled=enable;out.businessEnabled=false;
  if(enable===false){
   // Disable and confirm first. Evidence failures must never undo the stop.
   out.stopConfirmed=true;out.postStopEvidenceVerified=false;
   try{
    const ss=SpreadsheetApp.openById(sheet),store=juogSessionStoreB2_(ss,c);
    out.sessionEvents=store.read().events.length;
    const rows=ss.getSheetByName('D3_Journal').getDataRange().getValues();
    out.businessBaselineUnchanged=rows.length===165&&rows.every(r=>r.length===6)&&store.hash(JSON.stringify(rows))==='1414934e5e059e3cc7882486fa7cf5ee14afe99b4ab5dce9736a3c665d0b0797';
    out.postStopEvidenceVerified=out.businessBaselineUnchanged;
   }catch(_){out.postStopEvidenceVerified=false;}
  }
 }catch(e){
  // Never return exception text. Best-effort fail-closed after an uncertain enable.
  if(attempted&&enable===true&&p){try{
   const latestRaw=p.getProperty('UNIFIED_ISOLATION_CONFIG'),latest=JSON.parse(latestRaw);
   if(!latest||latest.environment!=='ISOLATED_TEST'||latest.spreadsheetId!==sheet||latest.approvedSpreadsheetId!==sheet||latest.sessionExecutionStage!=='AUTH_CONNECT'||latest.sessionPolicy!=='isolated_gas_session_b2')throw Error('TARGET');
   if(p.getProperty('UNIFIED_ISOLATION_CONFIG')!==latestRaw)throw Error('CONCURRENT');
   latest.authConnectReviewApproved=false;const stopped=JSON.stringify(latest);
   p.setProperty('UNIFIED_ISOLATION_CONFIG',stopped);out.stopConfirmed=p.getProperty('UNIFIED_ISOLATION_CONFIG')===stopped;
  }catch(_){out.stopConfirmed=false;}}
  const safe=['TARGET','BUSY','CONFIG','BUSINESS_GUARD','REVIEW','BASELINE','CONCURRENT','UNCERTAIN','SESSION_STORE_INVALID','SESSION_STORE_UNAVAILABLE'];
  out.error=e&&safe.includes(e.message)?e.message:'GATE_CHECK_OR_UPDATE_FAILED';
 }finally{if(locked)lock.releaseLock();}
 console.info(JSON.stringify(out));return out;
}
function juogEnableSingleApprovedAuthProbe(){return juogAuthProbeGate_(true);}
function juogStopApprovedAuthProbe(){return juogAuthProbeGate_(false);}

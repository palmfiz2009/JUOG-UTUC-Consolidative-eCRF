/* Recovery resume: exact 44-row journal pin; one pending JUOG-970 day90 intent. No journal mutation by this helper. */
/* Editor-only nonsecret configuration. No credential-property reads or web route. */
function juogAuth04RecoveryModeAdmin_(enable,readOnly=false){
 if(typeof enable!=='boolean'||typeof readOnly!=='boolean'||(readOnly&&!enable)){console.info('AUTH04_MODE_ARGUMENT_REFUSED');return false;}
 const script='11wSp4ePaP5b5A2b5ITZZSZa3YTe-Ex-Tu6oGlEkkRfkPrMCA4deVSZDy',sheet='1Hd6EHDPZe8zGcDbILkaBLubgF5atfAzRfpPSN5LemiU',generation='d72bcf33-423d-4c4d-862d-2e2d69bc3edf';
 const lock=LockService.getScriptLock();if(!lock.tryLock(30000)){console.info('AUTH04_MODE_LOCK_REFUSED');return false;}
 let props=null,denyConfig=null,writeAttempted=false;
 try{
  if(ScriptApp.getScriptId()!==script)throw Error('TARGET');
  props=PropertiesService.getScriptProperties();const raw=props.getProperty('UNIFIED_ISOLATION_CONFIG'),c=JSON.parse(raw||'null');
  if(!c||c.environment!=='ISOLATED_TEST'||c.spreadsheetId!==sheet||c.approvedSpreadsheetId!==sheet||c.sessionPolicy!=='isolated_gas_session_b2'||c.sessionStoreGeneration!==generation)throw Error('TARGET');
  if(enable){
   if(c.sessionExecutionStage!=='AUTH_CONNECT'||c.sessionStoreApproved!==true||c.authConnectReviewApproved!==true||typeof c.authConnectReviewRef!=='string'||!c.authConnectReviewRef.trim()||typeof c.approvalRef!=='string'||!c.approvalRef.trim()||c.notificationsDisabled!==true||c.backupVerified!==true||c.fictionalBaselineVerified!==true||c.qaApproved!==true||c.allRoutesReviewed!==false||c.schemaParityApproved!==false)throw Error('GATES');
   const hash=s=>Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256,s,Utilities.Charset.UTF_8).map(b=>('0'+((b+256)%256).toString(16)).slice(-2)).join('');
   const ss=SpreadsheetApp.openById(sheet),acl=ss.getSheetByName('V3_Users').getDataRange().getValues();
   if(acl.length!==2||JSON.stringify(acl[0])!==JSON.stringify(['issuer','subject','user_id','enabled','role','facility_ids_json','valid_until'])||acl[1][2]!=='UAT_TEST01_PI_01'||acl[1][3]!==true||acl[1][4]!=='facility'||acl[1][5]!=='["TEST01"]'||acl[1][6]!=='2026-11-19T23:59:00+09:00'||Date.now()>=new Date(acl[1][6]).getTime())throw Error('ACL');
   if(hash(JSON.stringify(['JUOG-ACL-PROPOSAL-v1',String(acl[1][0]),String(acl[1][1])]))!=='f0ea0ddb132e96bbd08cba4e37dc38609b73db5740530a05225c5acb6cab798f')throw Error('ACL');
   const journal=ss.getSheetByName('D3_Journal').getDataRange().getValues();
   if(hash(JSON.stringify(journal))!=='10ce07ef859fe6d14b3f8522c2e14153ce47b26d131f64ba0d89f9186c813399')throw Error('JOURNAL');
   // Readiness uses the very same pre-write guards and exits before changing
   // either the in-memory stage or any property. It does not authorize enable.
   if(readOnly){console.info(JSON.stringify({ok:true,readiness_only:true,configuration_changed:false,stage:'AUTH_CONNECT',fixed_scope:'TEST01/JUOG-970',journal_sha256:'10ce07ef859fe6d14b3f8522c2e14153ce47b26d131f64ba0d89f9186c813399',deployment_verified_by_this_function:false}));return true;}
   c.sessionExecutionStage='AUTH04_APPROVED';c.auth04ScopeReviewed=true;
   c.auth04ScopeReviewRef='a1131b9227fc54d0dcdd7d265985139837f57816/uat_evidence/auth04_scoped_gate_review_20261113.json';
   c.auth04FixtureProvisioned=true;c.auth04FixtureManifestSha256='0747f9ac3f59a6e230cc6cc6debaebde3138578ec82741567e995ab1e2d0d126';
   c.auth04ExecutionApprovalRef='PI_INTEGRATED_EXECUTION_20261113_SAME_OPERATION_RECOVERY';
  }else{c.sessionExecutionStage='AUTH_CONNECT';c.auth04ScopeReviewed=false;c.auth04ExecutionApprovalRef=null;}
  // A write may take effect even if its acknowledgement/readback fails. Always
  // prepare the restrictive state before attempting the write. Disable failures
  // must never restore a previously enabled state.
  const denied=JSON.parse(JSON.stringify(c));denied.sessionExecutionStage='AUTH_CONNECT';denied.auth04ScopeReviewed=false;denied.auth04ExecutionApprovalRef=null;denyConfig=JSON.stringify(denied);
  const next=JSON.stringify(c);writeAttempted=true;props.setProperty('UNIFIED_ISOLATION_CONFIG',next);
  if(props.getProperty('UNIFIED_ISOLATION_CONFIG')!==next)throw Error('READBACK');
  console.info(JSON.stringify({ok:true,stage:c.sessionExecutionStage,nonsecret_configuration_only:true}));return true;
 }catch(_){
  if(writeAttempted&&props&&denyConfig){
   try{props.setProperty('UNIFIED_ISOLATION_CONFIG',denyConfig);if(props.getProperty('UNIFIED_ISOLATION_CONFIG')===denyConfig){console.info('AUTH04_MODE_FAILED_RESTRICTIVE_STATE_VERIFIED');return false;}}catch(_){}
   console.info('AUTH04_MODE_STATE_UNCONFIRMED_STOP_AND_DISABLE_REQUIRED');return false;
  }
  console.info('AUTH04_MODE_CHANGE_REFUSED_NO_WRITE');return false;
 }finally{lock.releaseLock();}
}
function juogResumePendingAuth04(){return juogAuth04RecoveryModeAdmin_(true);}
function juogDisableRecoveryAuth04(){return juogAuth04RecoveryModeAdmin_(false);}
function juogCheckPendingAuth04Readiness(){return juogAuth04RecoveryModeAdmin_(true,true);}

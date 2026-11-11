/* Separate review candidate; does not run on load or create/change any sheet.
 * Existing doPost routing must be replaced, not extended with a legacy fallback.
 * Server identity bridge and individual ACL require approved OIDC/configuration. Missing config fails closed.
 */
function juogV3ReleaseConfig_(){
  const props=PropertiesService.getScriptProperties();
  const raw=props.getProperty('JUOG_V3_RELEASE_CONFIG');if(!raw)throw Error('RELEASE_NOT_APPROVED');
  const c=JSON.parse(raw);c.signingKey=props.getProperty('JUOG_V3_BRIDGE_SIGNING_KEY');
  if(!c.spreadsheetId || c.spreadsheetId!==c.approvedSpreadsheetId)throw Error('TARGET_NOT_APPROVED');
  return c;
}
function juogV3RegistryFromSheet_(ss,id){
 const sh=ss.getSheetByName('Registry');if(!sh)throw Error('REGISTRY_MISSING');
 const rows=sh.getDataRange().getValues(),idx={};rows[0].forEach((k,i)=>idx[k]=i);
 if(['registration_id','status','facility_code','registered_at','consent_date'].some(k=>idx[k]===undefined))throw Error('REGISTRY_SCHEMA');
 const matches=rows.slice(1).filter(r=>String(r[idx.registration_id])===id);if(matches.length!==1)return null;
 const r=matches[0],date=v=>v instanceof Date?Utilities.formatDate(v,'Asia/Tokyo','yyyy-MM-dd'):String(v||'').slice(0,10);
 return {status:String(r[idx.status]),facility_code:String(r[idx.facility_code]),registration_date:date(r[idx.registered_at]),consent_date:date(r[idx.consent_date])};
}
function juogV3ApiEntry_(envelope) {
  try {
    const config=juogV3ReleaseConfig_();
    if(config.environment!=='TEST'||config.reviewed!==true||config.backupVerified!==true||config.schemaParityApproved!==true||config.migrationComplete!==true) return {ok:false,error:'RELEASE_NOT_APPROVED'};
    // Do not trust client actor, role, facility claims or a common API token as user identity.
    const decoded=juogV3DecodeBridge_(envelope,config),body=decoded.request;
    const ss=SpreadsheetApp.openById(config.spreadsheetId);
    const service=new JuogSaveServiceV3({
      verifyIdentity:assertion=>{if(assertion!==envelope.identity_assertion)throw Error('AUTH_INVALID');return juogV3DecodeBridge_(envelope,config).principal;},
      directory:(issuer,subject)=>juogV3ReadIndividualAcl_(ss,issuer,subject),
      registry:id=>juogV3RegistryFromSheet_(ss,id),
      privacy:containsDirectIdentifier_,redact:stripDirectIdentifiers_,validate:validateClinicalV3,
      hash:s=>Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256,s,Utilities.Charset.UTF_8).map(b=>('0'+((b+256)%256).toString(16)).slice(-2)).join(''),
      today:()=>Utilities.formatDate(new Date(),'Asia/Tokyo','yyyy-MM-dd'),now:()=>new Date().toISOString(),
      withLock:f=>{const lock=LockService.getScriptLock();if(!lock.tryLock(30000)){const e=Error();e.safeCode='LOCK_TIMEOUT';throw e;}try{return f();}finally{lock.releaseLock();}},
      store:juogV3SheetsStore_(config.spreadsheetId)
    });
    if(body.action==='save_crf')return service.save(envelope.identity_assertion,body.payload);
    if(body.action==='read_crf')return service.read(envelope.identity_assertion,body.payload.record_key);
    if(body.action==='recover_crf_transaction')return service.recover(envelope.identity_assertion,body.payload.transaction_id,body.payload.reason);
    // Drafts, screening, MDT and other actions require explicit migrated handlers.
    // An unimplemented route MUST NOT fall through to the old permissive dispatcher.
    return {ok:false,error:'ROUTE_NOT_MIGRATED'};
  }catch(e){return {ok:false,error:'SERVICE_NOT_READY'};}
}
function juogV3SheetsStore_(spreadsheetId) {
  const ss=SpreadsheetApp.openById(spreadsheetId),names={intents:'V3_Intents',records:'V3_Records',audits:'V3_Audit',events:'V3_Events'};
  function tab(kind){const s=ss.getSheetByName(names[kind]);if(!s)throw Error('STORE_NOT_PROVISIONED');const h=s.getRange(1,1,1,2).getValues()[0];if(h[0]!=='transaction_id'||h[1]!=='entry_json')throw Error('STORE_SCHEMA_MISMATCH');return s;}
  function read(){const out={};for(const kind of Object.keys(names)){const rows=tab(kind).getDataRange().getValues();out[kind]=rows.slice(1).filter(r=>r.some(v=>v!==''&&v!==null)).map(r=>{if(typeof r[1]!=='string')throw Error('CORRUPT_STORE');const obj=JSON.parse(r[1]);if(obj.transaction_id!==r[0])throw Error('CORRUPT_STORE');return obj;});}return out;}
  function append(kind,obj){if(!/^[A-Za-z0-9_-]{1,128}$/.test(obj.transaction_id))throw Error('INVALID_TRANSACTION_ID');const json=JSON.stringify(obj);if(json.length>45000)throw Error('CELL_SIZE_LIMIT');tab(kind).appendRow([obj.transaction_id,json]);SpreadsheetApp.flush();}
  return {read,assertFits:i=>{if(JSON.stringify(i).length>40000 || JSON.stringify({evidence:i.auditEvidence}).length>40000)throw Error('TRANSACTION_TOO_LARGE');},appendIntent:o=>append('intents',o),appendRecord:o=>append('records',o),appendAudit:o=>append('audits',o),appendEvent:o=>append('events',o)};
}

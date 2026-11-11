/* Dedicated isolation project ONLY. Never add this doPost alongside legacy doPost.
 * All config is loaded server-side; request cannot supply gates or keys.
 * Properties are provisioned by administrator only after approval. */
function doPost(e){
 try{
  const props=PropertiesService.getScriptProperties(),raw=props.getProperty('UNIFIED_ISOLATION_CONFIG');
  if(!raw)return ContentService.createTextOutput(JSON.stringify({ok:false,error:'ISOLATION_NOT_APPROVED'})).setMimeType(ContentService.MimeType.JSON);
  const c=JSON.parse(raw);
  c.signingKey=props.getProperty('ADMIN_BRIDGE_SIGNING_KEY');
  c.resumeDerivationKey=props.getProperty('ADMIN_RESUME_DERIVATION_KEY');
  c.draftPepper=props.getProperty('ADMIN_DRAFT_PEPPER');
  const result=juogUnifiedIsolationEntryV3_(JSON.parse(e.postData.contents),c);
  return ContentService.createTextOutput(JSON.stringify(result)).setMimeType(ContentService.MimeType.JSON);
 }catch(_){return ContentService.createTextOutput(JSON.stringify({ok:false,error:'REQUEST_REJECTED'})).setMimeType(ContentService.MimeType.JSON);}
}

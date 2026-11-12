/* Concrete server-to-server assertion verifier. OIDC authentication is performed by
 * Streamlit; this bridge trusts only the configured server signing key, not a form email.
 * Config and individual ACL provisioning require approval; no default secrets. */
function juogV3DecodeBridge_(envelope,config) {
  if(!envelope || typeof envelope.request_json!=='string' || typeof envelope.identity_assertion!=='string')throw Error('AUTH_REQUIRED');
  if(envelope.request_json.length>200000||envelope.identity_assertion.length>8192)throw Error('AUTH_INVALID');
  if(!config || typeof config.signingKey!=='string'||config.signingKey.length<32||!config.bridgeIssuer||!config.audience||!config.oidcIssuer)throw Error('AUTH_NOT_CONFIGURED');
  const parts=envelope.identity_assertion.split('.');if(parts.length!==2||parts.some(p=>!/^[A-Za-z0-9_-]+$/.test(p)))throw Error('AUTH_INVALID');
  const signature=Utilities.computeHmacSha256Signature(parts[0],config.signingKey,Utilities.Charset.UTF_8);
  const supplied=Utilities.base64DecodeWebSafe(parts[1]);
  let diff=signature.length^supplied.length;for(let i=0;i<signature.length;i++)diff|=(signature[i]&255)^((supplied[i]||0)&255);if(diff!==0)throw Error('AUTH_INVALID');
  const c=JSON.parse(Utilities.newBlob(Utilities.base64DecodeWebSafe(parts[0])).getDataAsString('UTF-8'));
  const now=Math.floor(Date.now()/1000);
  if(![1,2].includes(c.v)||c.iss!==config.bridgeIssuer||c.aud!==config.audience||c.oidc_issuer!==config.oidcIssuer||typeof c.sub!=='string'||!c.sub||!Number.isInteger(c.iat)||!Number.isInteger(c.exp)||c.iat>now+5||c.exp-c.iat>60||c.exp<=c.iat)throw Error('AUTH_INVALID');
  if(c.exp<=now)throw Error('AUTH_EXPIRED');
  const digest=Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256,envelope.request_json,Utilities.Charset.UTF_8).map(b=>('0'+((b+256)%256).toString(16)).slice(-2)).join('');
  if(digest!==c.request_hash)throw Error('REQUEST_SIGNATURE_MISMATCH');
  const request=JSON.parse(envelope.request_json);
  if(!request||typeof request!=='object'||Array.isArray(request)||Object.keys(request).some(k=>!['action','payload'].includes(k))||typeof request.action!=='string')throw Error('REQUEST_INVALID');
  let session=null;
  if(config.sessionPolicy==='isolated_gas_session_b2'){
    if(c.v!==2||!c.session||c.session.generation!==config.sessionStoreGeneration||c.exp-c.iat>15||c.iat>now||!c.session||!/^[a-f0-9]{64}$/.test(c.session.sid)||!/^[a-f0-9]{32}$/.test(c.session.jti)||!Number.isInteger(c.session.token_iat)||!Number.isInteger(c.session.deadline)||c.session.token_iat>now||c.session.token_iat<0||c.session.deadline>c.session.token_iat+3600||c.session.deadline<=now||c.exp>c.session.deadline)throw Error('SESSION_INVALID');
    session=c.session;
  }else if(c.v!==1)throw Error('AUTH_INVALID');
  return {request,principal:{issuer:c.oidc_issuer,subject:c.sub},expires:c.exp,version:c.v,session};
}
function juogV3ReadIndividualAcl_(ss,issuer,subject) {
  const sh=ss.getSheetByName('V3_Users');if(!sh)throw Error('ACL_NOT_CONFIGURED');
  const rows=sh.getDataRange().getValues();
  if(!rows.length || !Array.isArray(rows[0]))throw Error('ACL_SCHEMA');
  const h=rows[0],idx={};
  if(new Set(h).size!==h.length)throw Error('ACL_SCHEMA');
  h.forEach((k,i)=>idx[k]=i);
  const required=['issuer','subject','user_id','enabled','role','facility_ids_json','valid_until'];if(required.some(k=>idx[k]===undefined))throw Error('ACL_SCHEMA');
  const matches=rows.slice(1).filter(r=>String(r[idx.issuer])===issuer&&String(r[idx.subject])===subject);
  if(matches.length!==1)return null;const r=matches[0],facilities=JSON.parse(String(r[idx.facility_ids_json]||'[]'));
  if(!Array.isArray(facilities)||facilities.some(x=>typeof x!=='string'||!x))throw Error('ACL_INVALID');
  const roles=['facility','admin','recovery_admin','radiology','medical_oncology','urology'];
  if(!roles.includes(r[idx.role]))throw Error('ACL_INVALID');
  const expiry=new Date(r[idx.valid_until]);const enabled=(r[idx.enabled]===true||r[idx.enabled]==='TRUE')&&Number.isFinite(expiry.getTime())&&expiry.getTime()>Date.now();
  const id=String(r[idx.user_id]||'').trim();
  if(!id)throw Error('ACL_INVALID');
  return {id,enabled,role:r[idx.role],facilities};
}
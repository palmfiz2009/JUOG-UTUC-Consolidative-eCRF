/* Review-only durable session/replay guard. Called ONLY inside the unified ScriptLock.
 * Exactly one GAS project owns this store. No direct Sheets/alternate-project writers.
 * Provision header and head property separately; NEVER recreate at runtime.
 */
function juogSessionStoreB2_(ss,c) {
 const header=['sequence','event_json','chain_sha256'];
 const sh=ss.getSheetByName('V3_SessionEvents');
 if(!sh||!c.sessionStoreGeneration||c.sessionStoreApproved!==true)throw Error('SESSION_STORE_UNAVAILABLE');
 const props=PropertiesService.getScriptProperties(),key='JUOG_B2_HEAD_'+c.spreadsheetId;
 const hash=s=>Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256,s,Utilities.Charset.UTF_8).map(b=>('0'+((b+256)%256).toString(16)).slice(-2)).join('');
 const genesis=hash('JUOG-B2|'+c.spreadsheetId+'|'+c.sessionStoreGeneration);
 function read(){
  const rows=sh.getDataRange().getValues();
  if(JSON.stringify(rows[0])!==JSON.stringify(header)||rows.length>10001)throw Error('SESSION_STORE_INVALID');
  let chain=genesis;const events=[];
  for(let i=1;i<rows.length;i++){
   const r=rows[i];if(r.length!==3||r[0]!==i||typeof r[1]!=='string')throw Error('SESSION_STORE_INVALID');
   chain=hash(chain+'|'+i+'|'+r[1]);if(chain!==r[2])throw Error('SESSION_STORE_INVALID');
   const e=JSON.parse(r[1]);
   if(!e||!['OPEN','USE','REVOKE'].includes(e.kind)||!/^[a-f0-9]{64}$/.test(e.sid)||!/^[a-f0-9]{64}$/.test(e.owner)||!Number.isInteger(e.deadline)||typeof e.jti!=='string')throw Error('SESSION_STORE_INVALID');
   events.push(e);
  }
  if(props.getProperty(key)!==(events.length+':'+chain))throw Error('SESSION_STORE_INVALID');
  return {events,chain};
 }
 function append(e){
  const old=read(),seq=old.events.length+1,json=JSON.stringify(e),chain=hash(old.chain+'|'+seq+'|'+json);
  if(seq>10000)throw Error('SESSION_STORE_FULL');
  // Reserve the expected head BEFORE the append. An uncertain write permanently
  // closes the gate until an explicit administrator recovery, never permits reuse.
  props.setProperty(key,seq+':'+chain);
  sh.appendRow([seq,json,chain]);SpreadsheetApp.flush();read();
 }
 return {read,append,hash};
}
function juogSessionGateB2_(ss,c,auth,who) {
 const a=auth.session,now=()=>Math.floor(Date.now()/1000);
 if(!a||auth.version!==2||c.sessionPolicy!=='isolated_gas_session_b2')throw Error('SESSION_REQUIRED');
 const store=juogSessionStoreB2_(ss,c),owner=store.hash(JSON.stringify([auth.principal.issuer,auth.principal.subject]));
 const events=store.read().events.filter(e=>e.sid===a.sid);
 if(events.some(e=>e.owner!==owner||e.deadline!==a.deadline))throw Error('SESSION_INVALID');
 if(events.filter(e=>e.kind==='OPEN').length>1)throw Error('SESSION_STORE_INVALID');
 const revoke=auth.request.action==='session_revoke';
 if(events.some(e=>e.jti===a.jti))throw Error('ASSERTION_REPLAY');
 if(events.some(e=>e.kind==='REVOKE')){
  if(revoke)return {response:{ok:true,revoked:true},guard:()=>{throw Error('SESSION_REVOKED');}};
  throw Error('SESSION_REVOKED');
 }
 function checkAcl(){
  const u=juogV3ReadIndividualAcl_(ss,auth.principal.issuer,auth.principal.subject);
  if(!u||!u.enabled||!['facility','admin','recovery_admin','radiology','medical_oncology','urology'].includes(u.role)||u.facilities.length!==1||u.facilities[0]!=='TEST01')throw Error('ACL_DENIED');
  return u;
 }
 if(!revoke)checkAcl();
 if(!events.length)store.append({kind:'OPEN',sid:a.sid,owner,deadline:a.deadline,jti:''});
 store.append({kind:revoke?'REVOKE':'USE',sid:a.sid,owner,deadline:a.deadline,jti:a.jti});
 function guard(){
  if(now()>=a.deadline||now()>=auth.expires)throw Error('AUTH_EXPIRED');
  const current=store.read().events.filter(e=>e.sid===a.sid);
  if(!current.some(e=>e.kind==='OPEN')||current.some(e=>e.kind==='REVOKE'))throw Error('SESSION_REVOKED');
  const u=checkAcl();
  if(!who||u.id!==who.id||u.role!==who.role||JSON.stringify(u.facilities)!==JSON.stringify(who.facilities))throw Error('ACL_CHANGED');
 }
 if(revoke)return {response:{ok:true,revoked:true},guard};
 guard();return {guard};
}

/* Read-only reconciliation. Never repairs on read, never infers a UUID. */
function pr15Recovery_(ss,journal,who,q){
 const key=[q.registration_id,q.crf_type,q.visit].join('|');
 // This reconciliation is read-only inside the caller's single-writer lock.
 // Reuse this fresh record scan for its rows and version: there is no write
 // between them. Do not retain it across requests or cache ACL/session data.
 const events=journal.read().filter(e=>e.key===key),snapshot=pr15Records_(ss,q.registration_id);
 const records=snapshot.rows.filter(r=>r.record_key===key);
 const audits=pr15Rows_(ss,'CRFSubmissionAudit',['submission_id','record_key','record_version','facility_code','registration_id','sheet_name']).rows;
 const uuids=[...new Set(events.filter(e=>e.actor===who.id).map(e=>e.uuid))],operations=[];
 for(const uuid of uuids){
  const own=events.filter(e=>e.uuid===uuid),intent=own.filter(e=>e.kind==='INTENT'),commit=own.filter(e=>e.kind==='COMMIT');
  const body=records.filter(r=>r.submission_id===uuid),audit=audits.filter(r=>r.submission_id===uuid);
  let state='NEEDS_RECONCILIATION',version=null;
  const valid=intent.length===1&&own.every(e=>e.actor===who.id&&e.key===key&&e.digest===intent[0].digest&&e.expected===intent[0].expected)&&intent[0].payload&&pr15Hash_(JSON.stringify(intent[0].payload))===intent[0].digest&&intent[0].payload.record_key===key&&intent[0].payload.submission_id===uuid&&intent[0].payload.facility_code==='TEST01';
  if(valid){
   const i=intent[0],bodyOK=body.length===1&&body[0].facility_code==='TEST01'&&body[0].payload_json===JSON.stringify(i.payload)&&Number(body[0].record_version)===i.expected+1;
   const auditOK=audit.length===1&&audit[0].record_key===key&&Number(audit[0].record_version)===i.expected+1&&audit[0].facility_code==='TEST01'&&audit[0].registration_id===q.registration_id&&audit[0].sheet_name===crfSheetForType_(q.crf_type);
   if(bodyOK&&auditOK&&commit.length===1&&commit[0].receipt&&commit[0].receipt.record_version===i.expected+1&&commit[0].receipt.submission_id===uuid){state='SAVED';version=i.expected+1;}
   else if(!commit.length&&body.length<=1&&audit.length<=1&&(bodyOK||!body.length)&&(!audit.length||auditOK)&&!events.some(e=>e.uuid!==uuid&&e.kind==='INTENT'&&!events.some(x=>x.uuid===e.uuid&&x.kind==='COMMIT'))){
    const current=snapshot.versions[key];
    if(current===i.expected+(bodyOK?1:0))state='RETRY_ALLOWED';
   }
  }
  operations.push({uuid,state,version,digest:intent.length===1?intent[0].digest:null,audit_verified:state==='SAVED'});
 }
 const unmatched=events.some(e=>e.actor!==who.id)||records.some(r=>!uuids.includes(r.submission_id));
 return {record_key:key,operations,state:unmatched||operations.some(x=>x.state==='NEEDS_RECONCILIATION')?'NEEDS_RECONCILIATION':operations.some(x=>x.state==='RETRY_ALLOWED')?'RETRY_ALLOWED':operations.length?'SAVED':'NO_SERVER_RECORD',new_submission_allowed:false};
}

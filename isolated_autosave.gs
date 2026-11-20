/* Append-only section drafts: each row is both the complete section and its audit.
 * Called only inside juogPr15Entry_'s signed ACL/session/owner-checked ScriptLock.
 * No Registry/CRF/version writes, no legacy token endpoint, no email. */
function pr15Canonical_(v){
 if(v===null||typeof v!=='object')return JSON.stringify(v);
 if(Array.isArray(v))return '['+v.map(pr15Canonical_).join(',')+']';
 return '{'+Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+pr15Canonical_(v[k])).join(',')+'}';
}
function pr15SectionDraft_(ss,who,q,action,guard){
 const page={perioperative_30d:'peri',day90:'d90',followup:'fu'}[q.crf_type];
 if(!page||!pr15Pair_(q,false))throw Error('VISIT_INVALID');
 const allowed=['registration_id','facility_code','crf_type','visit'];
 if(action==='save_section')allowed.push('section','data','operation_id','expected_revision','record_version');
 if(Object.keys(q).some(k=>!allowed.includes(k)))throw Error('REQUEST_INVALID');
 const key=[q.registration_id,q.crf_type,q.visit].join('|');
 const version=pr15Records_(ss,q.registration_id).versions[key];
 const table=()=>pr15Rows_(ss,'R1_DraftEvents',['event_json','digest']);
 function read(){
  const state={},events=[],ids=new Set();
  for(const row of table().rows){
   if(row.digest!==pr15Hash_(row.event_json))throw Error('DRAFT_STORE_INVALID');
   const e=JSON.parse(row.event_json);
   if(e.action!=='SECTION_SAVE')continue;
   if(!e.key||!e.actor||!Number.isInteger(e.record_version)||!Number.isInteger(e.revision)||!e.operation_id||!e.data||e.digest!==pr15Hash_(pr15Canonical_(e.data)))throw Error('DRAFT_STORE_INVALID');
   if(ids.has(e.operation_id))throw Error('DRAFT_STORE_INVALID');ids.add(e.operation_id);
   events.push(e);
   if(e.key!==key)continue;
   if(e.actor!==who.id)throw Error('SUBJECT_FORBIDDEN');
   if(e.record_version!==version)continue;
   if(!PR15_SECTIONS_[page][e.section]||e.revision!==(state[e.section]?.revision||0)+1)throw Error('DRAFT_STORE_INVALID');
   if(Object.keys(e.data).some(k=>!PR15_SECTIONS_[page][e.section].keys.includes(k)))throw Error('DRAFT_STORE_INVALID');
   state[e.section]=e;
  }
  return {state,events};
 }
 let current=read();
 const response=()=>({ok:true,record_key:key,record_version:version,sections:current.state,audit_verified:true});
 if(action==='get_sections')return response();
 if(!PR15_SECTIONS_[page][q.section]||typeof q.operation_id!=='string'||!/^[-a-zA-Z0-9]{16,80}$/.test(q.operation_id)||!Number.isInteger(q.expected_revision)||q.expected_revision<0||q.record_version!==version)throw Error('DRAFT_CONFLICT');
 if(!q.data||Array.isArray(q.data)||typeof q.data!=='object'||JSON.stringify(q.data).length>100000||containsDirectIdentifier_(q.data))throw Error('DRAFT_DATA_INVALID');
 const patterns=PR15_SECTIONS_[page][q.section].keys;
 for(const k of Object.keys(q.data)){
  if(!patterns.some(p=>p.endsWith('*')?k.startsWith(p.slice(0,-1)):p===k))throw Error('DRAFT_DATA_INVALID');
  const v=q.data[k];
  if(!v||typeof v!=='object'||!['value','date','datetime'].includes(v.type)||!Object.prototype.hasOwnProperty.call(v,'value')||Object.keys(v).some(x=>!['type','value'].includes(x)))throw Error('DRAFT_DATA_INVALID');
  if(v.type==='date'&&(typeof v.value!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(v.value)||!Number.isFinite(Date.parse(v.value))||new Date(v.value).toISOString().slice(0,10)!==v.value))throw Error('DRAFT_DATA_INVALID');
  if(v.type==='datetime'&&(typeof v.value!=='string'||!Number.isFinite(Date.parse(v.value))))throw Error('DRAFT_DATA_INVALID');
  if(k.endsWith('_reporter_email')&&v.value&&v.value!=='fictional@example.invalid')throw Error('DRAFT_DATA_INVALID');
  if(k.endsWith('_registration_id')&&v.value!==q.registration_id)throw Error('DRAFT_DATA_INVALID');
  if(k==='fu_visit_month'&&v.value!==q.visit.replace('m','ヶ月')+(q.visit==='24m'?'（終了）':''))throw Error('DRAFT_DATA_INVALID');
 }
 const digest=pr15Hash_(pr15Canonical_(q.data)),same=current.events.filter(e=>e.operation_id===q.operation_id);
 if(same.length){
  const e=same[0];
  if(e.actor!==who.id||e.key!==key||e.section!==q.section||e.digest!==digest||e.record_version!==version||e.revision!==q.expected_revision+1)throw Error('DRAFT_CONFLICT');
  if(current.state[q.section]?.operation_id!==q.operation_id)throw Error('DRAFT_CONFLICT');
  return Object.assign(response(),{receipt:e,existing:true});
 }
 if((current.state[q.section]?.revision||0)!==q.expected_revision)throw Error('DRAFT_CONFLICT');
 const event={action:'SECTION_SAVE',key,section:q.section,actor:who.id,record_version:version,revision:q.expected_revision+1,operation_id:q.operation_id,digest,data:q.data,at:new Date().toISOString()};
 const json=JSON.stringify(event);guard();const count=table().rows.length;
 table().sh.appendRow([json,pr15Hash_(json)]);SpreadsheetApp.flush();
 const after=table().rows;if(after.length!==count+1||after[count].event_json!==json||after[count].digest!==pr15Hash_(json))throw Error('DRAFT_WRITE_UNCONFIRMED');
 guard();current=read();return Object.assign(response(),{receipt:current.state[q.section],existing:false});
}

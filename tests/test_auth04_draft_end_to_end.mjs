// Exercises actual GAS draft save/read functions end-to-end with an in-memory
// Google Sheets double. ALL records fictional; no network, app passwords, etc.
import fs from "node:fs";
import crypto from "node:crypto";
import assert from "node:assert/strict";

const source = fs.readFileSync("05_registry_google_apps_script.gs", "utf8");
function sliceBetween(start, end) {
  const a=source.indexOf(start), b=source.indexOf(end,a);
  assert(a>=0 && b>a, "GAS extraction boundary missing: "+start);
  return source.slice(a,b);
}
const privacy = sliceBetween("function directIdentifierKey_(key) {","function isCn1Only_(cT, cN, cM) {");
const draftFns = sliceBetween("function draftKey_(registrationId, crfType, visit) {","function resetDraftCode_(p) {");
const src = privacy+"\n"+draftFns;

// Actual field order matches existing CRF_Drafts schema. All values are synthetic.
const columns = ["draft_key","updated_at","registration_id","crf_type","visit",
 "facility_code","facility_name","reporter_email","schema_version","draft_json",
 "resume_code_hash","failed_attempts","locked_until","code_reset_at","code_reset_by",
 "email_reset_at","email_reset_by"];
function fixture() {
  const rows=[columns.slice()], count={locks:0,appends:0,updates:0,flushes:0};
  const sh={
    getDataRange:()=>({getValues:()=>rows.map(x=>x.slice())}),
    appendRow:(row)=>{count.appends++;rows.push(row.slice());},
  };
  const deps={
    Utilities:{
      DigestAlgorithm:{SHA_256:"SHA_256"},Charset:{UTF_8:"UTF_8"},
      computeDigest:(_,s)=>[...crypto.createHash("sha256").update(s).digest()].map(x=>x>127?x-256:x),
      formatDate:()=> "2026-11-16T00:00:00+09:00",
    },
    LockService:{getScriptLock:()=>({
      tryLock:()=>{count.locks++;return true}, releaseLock:()=>{}
    })},
    getSpreadsheet_:()=>({getSheetByName:()=>sh}),
    ensureSheetHeaders_:()=>sh,
    headerIndex_:keys=>Object.fromEntries(keys.map((x,i)=>[x,i])),
    CRF_DRAFT_SHEET:"CRF_Drafts", CRF_DRAFT_HEADERS:columns,
    TIMEZONE:"Asia/Tokyo",
    SpreadsheetApp:{flush:()=>count.flushes++},
    appendByHeaders_:(_,obj)=>sh.appendRow(columns.map(k=>obj[k]??"")),
    setByHeader_:(_,n,idx,obj)=>{
      count.updates++;
      for(const [key,value] of Object.entries(obj)){
        if(idx[key]!==undefined) rows[n-1][idx[key]]=value;
      }
    },
    isoDateTime_:v=>v instanceof Date?v.toISOString():String(v),
    validateSubject_:p=>({ok:true,facility_code:"TEST01",facility_name:"Fictional QA"}),
  };
  const fn = new Function(...Object.keys(deps),src+
    "\nreturn {saveScreeningDraft_,getScreeningDraft_,saveDraft_,getDraft_,screeningDraftId_,draftKey_};"
  )(...Object.values(deps));
  const applicant={
    facility_code:"TEST01",facility_name:"Fictional QA",
    local_subject_code:"QA-EXAMPLE",reporter_email:"qa@example.invalid",
    schema_version:"fictional-schema",
    draft_state:{reg_age:{type:"value",value:45},reg_consent_date:{type:"date",value:"2026-11-01"}}
  };
  return {rows,count,fn,applicant};
}
const check=(name,fn)=>{fn(); console.log("PASS",name)};

check("screening draft saves permitted clinical inputs and reads them back",()=>{
 const x=fixture(), r=x.fn.saveScreeningDraft_(x.applicant);
 assert.equal(r.ok,true);
 assert.equal(x.count.appends,1);
 const got=x.fn.getScreeningDraft_(x.applicant);
 assert.equal(got.ok,true); assert.equal(got.source_found,true);
 assert.deepEqual(got.draft_state,x.applicant.draft_state);
 assert.equal(x.rows.length,2);
});
check("complete birth date key in screening draft refused without lock or write",()=>{
 const x=fixture(),p={...x.applicant,draft_state:{...x.applicant.draft_state,reg_birth_date:{type:"date",value:"1980-01-02"}}};
 const got=x.fn.saveScreeningDraft_(p);
 assert.deepEqual({ok:got.ok,error:got.error},{ok:false,error:"DIRECT_IDENTIFIER_NOT_ALLOWED"});
 assert.equal(x.count.locks,0);assert.equal(x.rows.length,1);
});
check("nested JSON and free-text identifiers refused before writing",()=>{
 for(const bad of [
  {reg_note:"生年月日1980年1月2日"},
  {reg_note:JSON.stringify({nested:{regBirthDate:"1980-01-02"}})},
  {reg_note:"MRN: 999999"},
 ]){
  const x=fixture();
  const res=x.fn.saveScreeningDraft_({...x.applicant,draft_state:bad});
  assert.equal(res.error,"DIRECT_IDENTIFIER_NOT_ALLOWED");
  assert.equal(x.count.appends,0);
 }
});
check("legacy screening draft read redacts DOB without mutating persisted row",()=>{
 const x=fixture();
 const id=x.fn.screeningDraftId_("TEST01","QA-EXAMPLE");
 const key=x.fn.draftKey_(id,"screening","mdt_application");
 const legacy={reg_birth_date:{type:"date",value:"1980-01-02"},reg_age:{type:"value",value:45},comment:"生年月日1980年1月2日",allowed:"既往歴：高血圧"};
 const draftString=JSON.stringify(legacy);
 const row=columns.map(k=>({
  draft_key:key,updated_at:"2026-11-15T18:00:00+09:00",
  registration_id:id,crf_type:"screening",visit:"mdt_application",
  facility_code:"TEST01",facility_name:"Fictional QA",reporter_email:"qa@example.invalid",
  schema_version:"legacy",draft_json:draftString
 })[k]??"");
 x.rows.push(row);
 const returned=x.fn.getScreeningDraft_(x.applicant);
 assert.equal(returned.ok,true);
 assert.equal("reg_birth_date" in returned.draft_state,false);
 assert.equal(returned.draft_state.comment,"[REDACTED]");
 assert.equal(returned.draft_state.reg_age.value,45);
 assert.equal(returned.draft_state.allowed,"既往歴：高血圧");
 assert.equal(x.rows[1][columns.indexOf("draft_json")],draftString);
 assert.equal(x.count.updates,0);
});
check("screening wrong-owner e-mail cannot retrieve legacy draft",()=>{
 const x=fixture();x.fn.saveScreeningDraft_(x.applicant);
 const result=x.fn.getScreeningDraft_({...x.applicant,reporter_email:"different@example.invalid"});
 assert.equal(result.ok,false);assert.equal(result.error,"DRAFT_EMAIL_MISMATCH");
 assert.equal(JSON.stringify(result).includes("reg_age"),false);
});
check("corrupted draft JSON returns generic error without leaking source content",()=>{
 const x=fixture();x.fn.saveScreeningDraft_(x.applicant);
 x.rows[1][columns.indexOf("draft_json")]="<INVALID JSON FAKE DOB 1980-01-02>";
 const got=x.fn.getScreeningDraft_(x.applicant);
 assert.equal(got.ok,false);assert.equal(got.error,"DRAFT_PARSE_ERROR");
 assert.equal(JSON.stringify(got).includes("1980-01-02"),false);
});
check("post-registration save refuses identifier values with no write",()=>{
 const x=fixture();
 const p={registration_id:"JUOG-901",facility_code:"TEST01",crf_type:"day90",visit:"90d",reporter_email:"qa@example.invalid",
  draft_state:{freeText:"患者氏名:テスト患者"}};
 const res=x.fn.saveDraft_(p);
 assert.equal(res.ok,false);assert.equal(res.error,"DIRECT_IDENTIFIER_NOT_ALLOWED");
 assert.equal(x.count.appends,0);
});
check("post-registration legacy read redacts while preserving row",()=>{
 const x=fixture();
 const p={registration_id:"JUOG-901",facility_code:"TEST01",crf_type:"day90",visit:"90d",reporter_email:"qa@example.invalid",
 draft_state:{visit_date:{type:"date",value:"2026-11-15"}}};
 const r=x.fn.saveDraft_(p); assert.equal(r.ok,true);
 const stored={visit_date:{type:"date",value:"2026-11-15"},nested:{patientName:"SAMPLE",vital:"正常"}};
 const raw=JSON.stringify(stored);
 x.rows[1][columns.indexOf("draft_json")]=raw;
 const got=x.fn.getDraft_(p);
 assert.equal(got.ok,true);assert.equal(got.source_found,true);
 assert.deepEqual(got.draft_state,{visit_date:{type:"date",value:"2026-11-15"},nested:{vital:"正常"}});
 assert.equal(x.rows[1][columns.indexOf("draft_json")],raw);
});
console.log("ALL 8 FICTIONAL REAL-GAS DRAFT FLOW CHECKS PASSED");

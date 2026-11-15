// Run with: node tests/test_screening_identity.mjs
// In-memory Google Sheet fixtures only; no credentials, network calls, or real patients.
import fs from "node:fs";
import assert from "node:assert/strict";
const code = fs.readFileSync("05_registry_google_apps_script.gs", "utf8");
const start = code.indexOf("function screeningOriginalSubjectCodes_");
const end = code.indexOf("function listScreenings_(p)");
assert(start >= 0 && end > start, "screening helpers must exist");
const src = code.slice(start, end);

const header = ["screening_id","created_at","updated_at","status","review_round",
"facility_code","facility_name","local_subject_code","reporter_email","submission_id",
"consent_date","cT","cN","cM","best_effect","site_recist","planned_surgery",
"planned_surgery_date","mdt_date","central_recist","mdt_decision","mdt_reason",
"consensus_note","registration_id","registered_at","admin_user"];

function testCase(records = [], opts = {}) {
  const rows = [header, ...records.map(o => header.map(k => ({
    screening_id:o.id, status:o.status, review_round:o.round||1,
    facility_code:o.facility||"F06", facility_name:"FICTIONAL",
    local_subject_code:o.stored, reporter_email:o.email||"applicant@example.org",
    submission_id:o.submission||"prior-uuid", registration_id:o.registered||""
  })[k]??""))];
  const reg = [["facility_code","local_subject_code","status","registration_id"]];
  const audit = [["screening_id","review_round","action"]];
  const crf = [["screening_id","payload_json"],
    ...records.filter(o=>o.original).map(o=>[o.id,JSON.stringify({local_subject_code:o.original})])];
  const meter = {stored:0,formats:0,flush:0};
  const sheet = content => ({
    getDataRange:()=>({getValues:()=>content.map(r=>r.slice())}),
    getLastRow:()=>content.length,
    getLastColumn:()=>content[0].length,
    getRange:(r,c,n=1,m=1)=>({
      getValue:()=>content[r-1]?.[c-1],
      getValues:()=>Array.from({length:n},(_,i)=>Array.from({length:m},(_,j)=>content[r+i-1]?.[c+j-1]??"")),
      setNumberFormat:()=>{meter.formats++},
      setValue:v=>{content[r-1][c-1]=v}
    }),
    appendRow:x=>{content.push(x.slice())},
  });
  const db = {Screening:sheet(rows), Registry:sheet(reg),
              ScreeningAudit:sheet(audit), ScreeningCRF:sheet(crf)};
  const deps = {
    getSpreadsheet_:()=>({getSheetByName:n=>db[n]}),
    SCREENING_CRF_SHEET:"ScreeningCRF",SCREENING_SHEET:"Screening",
    REGISTRY_SHEET:"Registry",SCREENING_AUDIT_SHEET:"ScreeningAudit",
    headerIndex_:h=>Object.fromEntries(h.map((x,i)=>[x,i])),
    containsDirectIdentifier_:()=>false,
    validateScreeningHardStops_:()=>({ok:true}),
    LockService:{getScriptLock:()=>({tryLock:()=>true,releaseLock:()=>{}})},
    submissionExistsInSheet_:()=>opts.crfExists!==false,
    savePayloadToSheet_:()=>{meter.stored++;return {ok:true}},
    setByHeader_:(sh,rowNum,idx,obj)=>{
      const row = rows[rowNum-1];
      for (const [key,val] of Object.entries(obj))
        if (idx[key] !== undefined) row[idx[key]] = val;
    },
    appendByHeaders_:(sh,obj)=>{
      const columns=sh.getDataRange().getValues()[0];
      sh.appendRow(columns.map(k=>obj[k]??""));
    },
    nextScreeningId_:(values,idx)=>{
      const max=Math.max(0,...values.slice(1).map(r=>
        Number(String(r[idx.screening_id]||"").split("-").pop())||0));
      return "JUOG-SCR-"+String(max+1).padStart(3,"0");
    },
    SpreadsheetApp:{flush:()=>{meter.flush++}},
  };
  const fn = new Function(...Object.keys(deps),src+"\nreturn submitScreening_;")(...Object.values(deps));
  const user = {
    facility_code:opts.facility||"F06", facility_name:"FICTIONAL",
    local_subject_code:opts.subject||"01",
    reporter_email:opts.email||"applicant@example.org",
    submission_id:opts.submission||"fresh-uuid",
    consent_date:"2026-11-15",
    ct:"cT3",cn:"cN1",cm:"cM0",best_effect:"PR",site_recist:"PR",
    crf_payload:{data:{local_subject_code:opts.subject||"01"}}
  };
  return {result:fn(user),rows:rows.length-1,
          audit:audit.length-1, saved:meter.stored,formats:meter.formats};
}
const historic = Array.from({length:5},(_,i)=>({
  id:"JUOG-SCR-"+String(i+1).padStart(3,"0"),
  status:i===4?"PENDING":"VOID",stored:1,original:"01",submission:"prior-"+i
}));
const check=(name, rows, args, predicate)=>{
  const got=testCase(rows,args);
  assert(predicate(got),name+": "+JSON.stringify(got));
  console.log("PASS",name);
};
check("reuse 005, advance round",historic,{},x=>x.result.ok&&
      x.result.screening_id==="JUOG-SCR-005"&&x.result.review_round===2&&
      x.result.submission_replay===false&&x.rows===5);
check("same UUID never increments",historic,{submission:"prior-4"},x=>x.result.ok&&
      x.result.review_round===1&&x.result.submission_replay===true&&x.audit===0);
check("missing CRF snapshot is restored",[{id:"JUOG-SCR-001",status:"PENDING",stored:1,submission:"first"}],
      {submission:"first",crfExists:false},x=>x.result.ok&&x.saved===1&&x.rows===1);
check("HOLD repeat review",[{id:"JUOG-SCR-003",status:"HOLD",round:3,stored:"ABC",original:"ABC"}],
      {subject:"ABC"},x=>x.result.ok&&x.result.screening_id==="JUOG-SCR-003"&&x.result.review_round===4);
check("INELIGIBLE closed",historic.map(x=>({...x,status:x.id.endsWith("005")?"INELIGIBLE":"VOID"})),
      {},x=>x.result.error==="SCREENING_CLOSED"&&x.rows===5);
check("VOID only not recycled",historic.slice(0,4),{},
      x=>x.result.error==="SCREENING_IDENTITY_VOIDED"&&x.rows===4);
check("email mismatch blocked",historic,{email:"other@example.org"},
      x=>x.result.error==="REPORTER_EMAIL_MISMATCH"&&x.rows===5);
check("replay email mismatch blocked",historic,{email:"other@example.org",submission:"prior-4"},
      x=>x.result.error==="REPORTER_EMAIL_MISMATCH"&&x.audit===0);
check("01 is not 1",historic,{subject:"1"},
      x=>x.result.ok&&x.result.screening_id==="JUOG-SCR-006"&&x.formats===1);
check("02 is separate case",historic,{subject:"02"},
      x=>x.result.ok&&x.result.screening_id==="JUOG-SCR-006");
check("another facility separate",historic,{facility:"F07"},
      x=>x.result.ok&&x.result.screening_id==="JUOG-SCR-006");
check("duplicate active blocked",historic.map(x=>({...x,status:"PENDING"})),{},
      x=>x.result.error==="DUPLICATE_ACTIVE_SCREENING_IDENTITY");
check("no trusted original blocked",[{id:"JUOG-SCR-001",status:"PENDING",stored:1}],{},
      x=>x.result.error==="SCREENING_IDENTITY_UNVERIFIABLE");
check("new case",[],{},x=>x.result.ok&&x.result.screening_id==="JUOG-SCR-001");
console.log("ALL 14 IDENTITY CASES PASSED");

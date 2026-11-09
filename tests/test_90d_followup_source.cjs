/* Contract tests for real Apps Script CRF 30-day source validation.
 * In-memory fixture only; no deployed GAS/Sheets access or credentials.
 */
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const code = fs.readFileSync(path.resolve(__dirname, "..", "05_registry_google_apps_script.gs"), "utf8");
assert(code.includes("const sourceCheck = validateCrfSourceLink_(payload);"),
  "saveCrf_ must call the shared source validation");
const ctx = vm.createContext({});
vm.runInContext(code, ctx, { timeout: 5000 });
ctx.mockLatest = {
  ok: true, found: true, record_version: 2, submission_id: "SYNTHETIC-SOURCE-V2",
  facility_code: "F11",
  payload: { data: {surgery_performed:"実施しなかった", reference_date:"2026-03-01"} },
};
vm.runInContext("getLatestCrfPayload_ = function() { return mockLatest; };", ctx);
const payload = () => ({
  registration_id:"JUOG-999", facility_code:"F11", crf_type:"followup", visit:"6m",
  data:{
    source_30d_linked:true, source_30d_record_version:2,
    source_30d_submission_id:"SYNTHETIC-SOURCE-V2",
    surgery_performed:"実施しなかった", reference_date:"2026-03-01",
    visit_month:"6ヶ月",
  },
});
let passes=0;
function check(label, fn){fn();passes++;console.log("PASS "+label);}
check("valid linked 6m follow-up passes backend",()=>{
  assert.equal(ctx.validateCrfSourceLink_(payload()).ok, true);
});
check("follow-up rejects unlinked source",()=>{
  const p=payload();p.data.source_30d_linked=false;
  assert.equal(ctx.validateCrfSourceLink_(p).error,"SOURCE_CRF_REQUIRED");
});
check("follow-up rejects stale 30d version",()=>{
  const p=payload();p.data.source_30d_record_version=1;
  assert.equal(ctx.validateCrfSourceLink_(p).error,"SOURCE_CRF_UPDATED");
});
check("follow-up rejects wrong 30d submission identity",()=>{
  const p=payload();p.data.source_30d_submission_id="OTHER-SOURCE";
  assert.equal(ctx.validateCrfSourceLink_(p).error,"SOURCE_CRF_UPDATED");
});
check("follow-up rejects mismatched surgery date or surgery status",()=>{
  const p=payload();p.data.reference_date="2026-04-01";
  assert.equal(ctx.validateCrfSourceLink_(p).error,"SOURCE_CRF_CONTENT_MISMATCH");
  p.data.reference_date="2026-03-01";p.data.surgery_performed="実施した";
  assert.equal(ctx.validateCrfSourceLink_(p).error,"SOURCE_CRF_CONTENT_MISMATCH");
});
check("follow-up rejects wrong facility code",()=>{
  const p=payload();p.facility_code="F07";
  assert.equal(ctx.validateCrfSourceLink_(p).error,"SOURCE_CRF_CONTENT_MISMATCH");
});
check("follow-up rejects mismatch between visit and month",()=>{
  const p=payload();p.visit="9m";
  assert.equal(ctx.validateCrfSourceLink_(p).error,"FOLLOWUP_VISIT_MISMATCH");
  p.visit="25m";
  assert.equal(ctx.validateCrfSourceLink_(p).error,"FOLLOWUP_VISIT_MISMATCH");
});
check("all seven follow-up visits have correct labeled periods",()=>{
  for(const [visit,month] of Object.entries({
    "6m":"6ヶ月","9m":"9ヶ月","12m":"12ヶ月","15m":"15ヶ月",
    "18m":"18ヶ月","21m":"21ヶ月","24m":"24ヶ月（終了）"
  })){
    const p=payload();p.visit=visit;p.data.visit_month=month;
    assert.equal(ctx.validateCrfSourceLink_(p).ok,true,visit);
  }
});
check("90-day manual source fallback remains supported",()=>{
  const p=payload();p.crf_type="day90";p.visit="90d";p.data.source_30d_linked=false;
  assert.equal(ctx.validateCrfSourceLink_(p).ok,true);
});
check("linked 90-day source is validated",()=>{
  const p=payload();p.crf_type="day90";p.visit="90d";
  assert.equal(ctx.validateCrfSourceLink_(p).ok,true);
  p.data.source_30d_record_version=1;
  assert.equal(ctx.validateCrfSourceLink_(p).error,"SOURCE_CRF_UPDATED");
});
check("missing source CRF is rejected",()=>{
  ctx.mockLatest={ok:true,found:false};
  assert.equal(ctx.validateCrfSourceLink_(payload()).error,"SOURCE_CRF_MISSING");
});

// Hard validation uses the GAS Asia/Tokyo clock. It must independently reject
// future assessments even if a caller bypasses Streamlit's form validator.
ctx.Utilities = {formatDate: () => "2026-11-09"};
function validateDate(data) {
  const p = payload();
  p.data = {...p.data,...data};
  return ctx.validateCrfHardStops_(p,{
    registration_date:"2026-02-01", consent_date:"2026-02-01"
  });
}
check("valid past visit accepted by backend chronology hard stop",()=>{
  assert.equal(validateDate({visit_date:"2026-09-01",lab_date:"2026-09-01"}).ok,true);
});
check("future visit blocked at GAS boundary",()=>{
  const x=validateDate({visit_date:"2027-06-06"});
  assert.equal(x.error,"HARD_VALIDATION_FAILED");
  assert(x.message.includes("評価日が未来日"));
});
check("future clinical lab date blocked at GAS boundary",()=>{
  const x=validateDate({visit_date:"2026-09-01",lab_date:"2027-02-01"});
  assert.equal(x.error,"HARD_VALIDATION_FAILED");
  assert(x.message.includes("採血日が未来日"));
});
check("future death or last-alive date blocked at GAS boundary",()=>{
  for(const field of ["death_date","last_alive_date"]){
    const x=validateDate({visit_date:"2026-09-01",[field]:"2027-01-01"});
    assert.equal(x.error,"HARD_VALIDATION_FAILED",field);
  }
});

console.log("Completed "+passes+"/15 source-and-date-integrity checks.");

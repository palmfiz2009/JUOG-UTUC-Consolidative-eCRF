// Offline-only GAS regressions with wholly fictional in-memory rows.
// No network, secrets, Google Sheets, actual CRF records or deployment.
import assert from "node:assert/strict";
import fs from "node:fs";

const source=fs.readFileSync("05_registry_google_apps_script.gs","utf8");
function extract(start,end) {
  const a=source.indexOf(start), b=source.indexOf(end,a);
  assert(a>=0 && b>a, start+" not found");
  return source.slice(a,b);
}

const savedCode=extract("function savePayloadToSheet_(", "function submissionExistsInSheet_(");
const CRF_AUDIT_SHEET="CRFSubmissionAudit";
const SCREENING_CRF_SHEET="ScreeningCRF";
const auditedFields=["saved_at","sheet_name","record_key","record_version",
  "submission_id","submission_kind","registration_id","facility_code"];
const crfFields=["saved_at","record_version","submission_id","record_key",
  "submission_kind","correction_reason","submitted_at","registration_id",
  "facility_code","facility_name","reporter_email","crf_type","visit",
  "schema_version","study_code","payload_json"];

const fixture={
  registration_id:"JUOG-901",crf_type:"perioperative_30d",visit:"30d",
  record_key:"JUOG-901|perioperative_30d|30d",
  facility_code:"F99", facility_name:"完全架空施設",
  reporter_email:"fictional@example.invalid",
  submission_id:"fictional-uuid",submission_kind:"初回報告",
  submitted_at:"2026-11-15",data:{fictional:true}
};

function fakeFixture(payload=fixture, opts={}) {
  const flags={...opts};
  const crf=[crfFields,crfFields.map(k => ({
    record_version:1,
    submission_id:payload.submission_id,
    record_key:payload.record_key,
    registration_id:payload.registration_id,
    facility_code:payload.facility_code,
    payload_json:JSON.stringify(payload),
  })[k] ?? "")];
  const audit=[auditedFields];
  const sheet=rows=>({rows,getDataRange:()=>({getValues:()=>rows.map(r=>r.slice())})});
  const sheets={
    CRF_30d:sheet(crf),
    CRF_90d:sheet([crfFields]),
    CRF_Followup:sheet([crfFields]),
    [CRF_AUDIT_SHEET]:sheet(audit),
  };
  if(opts.auditMissing)delete sheets[CRF_AUDIT_SHEET];
  const getSpreadsheet_=()=>({getSheetByName:n=>sheets[n],getId:()=>"isolated-fixture-sheet"});
  const headerIndex_=h=>Object.fromEntries(h.map((key,i)=>[key,i]));
  const appendByHeaders_=(sh,obj)=>{
    if ((flags.dropAuditAppend && sh === sheets[CRF_AUDIT_SHEET]) ||
        (flags.dropCrfAppend && [sheets.CRF_30d,sheets.CRF_90d,sheets.CRF_Followup].includes(sh))) return;
    sh.rows.push(sh.rows[0].map(k=>obj[k]??""));
  };
  const compiled=new Function(
    "getSpreadsheet_","headerIndex_","flattenObject_","ensureDynamicHeaders_",
    "appendByHeaders_","validateDay90SourceLink_","SpreadsheetApp",
    "CRF_AUDIT_SHEET","SCREENING_CRF_SHEET",
    savedCode+"\nreturn {savePayloadToSheet_,ensureCrfAuditRow_};"
  )(
    getSpreadsheet_,headerIndex_,()=>({}),()=>{},appendByHeaders_,
    ()=>({ok:true}),{flush:()=>{}},CRF_AUDIT_SHEET,SCREENING_CRF_SHEET
  );
  return { ...compiled, sheets, appendByHeaders_, flags };
}

// In-memory 90-day and 6–24m follow-up save/replay/correction round-trip.
// The linked 30-day source itself is tested separately below.
for (const [sheetName,crfType,visit] of [
  ["CRF_90d","day90","90d"],
  ["CRF_Followup","followup","6m"],
  ["CRF_Followup","followup","12m"],
  ["CRF_Followup","followup","24m"],
]) {
  const x=fakeFixture();
  const initial={...fixture,
    crf_type:crfType,visit,
    record_key:`JUOG-901|${crfType}|${visit}`,
    submission_id:`fictional-${visit}-v1`,
    submission_kind:"初回報告",
  };
  const correction={...initial,
    submission_id:`fictional-${visit}-v2`,
    submission_kind:"訂正報告",correction_reason:"検証用訂正",
  };
  const first=x.savePayloadToSheet_(sheetName,initial,true);
  assert(first.ok && !first.existing && first.record_version===1,sheetName+" initial");
  assert.equal(first.record_key,initial.record_key);
  assert.equal(first.crf_type,crfType);
  assert.equal(first.visit,visit);
  assert.equal(first.spreadsheet_id,"isolated-fixture-sheet");
  assert.equal(first.audit_verified,true);
  assert.equal(x.sheets[sheetName].rows.length,2);
  const replay=x.savePayloadToSheet_(sheetName,initial,true);
  assert(replay.ok && replay.existing && replay.record_version===1,sheetName+" replay");
  assert.equal(replay.record_key,initial.record_key);
  assert.equal(replay.spreadsheet_id,"isolated-fixture-sheet");
  assert.equal(replay.audit_verified,true);
  assert.equal(x.sheets[sheetName].rows.length,2,sheetName+" replay cannot duplicate");
  const second=x.savePayloadToSheet_(sheetName,correction,true);
  assert(second.ok && !second.existing && second.record_version===2,sheetName+" correction");
  assert.equal(x.sheets[sheetName].rows.length,3);
  assert.equal(x.sheets[CRF_AUDIT_SHEET].rows.length,3,sheetName+" audit for v1+v2");
  const secondReplay=x.savePayloadToSheet_(sheetName,correction,true);
  assert(secondReplay.ok && secondReplay.existing && secondReplay.record_version===2);
  assert.equal(x.sheets[sheetName].rows.length,3);
  assert.equal(x.sheets[CRF_AUDIT_SHEET].rows.length,3);
  console.log("PASS",sheetName,visit,"v1/v2/replay/audit (fictional)");
}

{
  const x=fakeFixture();
  const first=x.savePayloadToSheet_("CRF_30d",fixture,true);
  assert(first.ok && first.existing && first.record_version===1);
  assert.equal(x.sheets.CRF_30d.rows.length,2,"replay cannot append a second CRF");
  assert.equal(x.sheets[CRF_AUDIT_SHEET].rows.length,2,"replay must repair missing audit row");
  const second=x.savePayloadToSheet_("CRF_30d",fixture,true);
  assert(second.ok && second.existing);
  assert.equal(x.sheets[CRF_AUDIT_SHEET].rows.length,2,"replay may not duplicate audit");
  console.log("PASS audit repair + repeat replay");
}
{
  const x=fakeFixture(fixture,{dropAuditAppend:true});
  const rejected=x.savePayloadToSheet_("CRF_30d",fixture,true);
  assert.equal(rejected.ok,false);
  assert.equal(rejected.error,"CRF_AUDIT_READBACK_MISMATCH");
  assert.equal(x.sheets.CRF_30d.rows.length,2,"failed audit cannot duplicate CRF body");
  x.flags.dropAuditAppend=false;
  const retried=x.savePayloadToSheet_("CRF_30d",fixture,true);
  assert(retried.ok && retried.existing);
  assert.equal(x.sheets.CRF_30d.rows.length,2);
  assert.equal(x.sheets[CRF_AUDIT_SHEET].rows.length,2);
  console.log("PASS silent audit write failure blocks success; same UUID repairs");
}
{
  const corrected={...fixture, submission_id:"fictional-correction-uuid",
    submission_kind:"訂正報告", correction_reason:"検証用の訂正"};
  const x=fakeFixture(fixture,{dropCrfAppend:true});
  const rejected=x.savePayloadToSheet_("CRF_30d",corrected,true);
  assert.equal(rejected.ok,false);
  assert.equal(rejected.error,"CRF_READBACK_MISMATCH");
  assert.equal(x.sheets.CRF_30d.rows.length,2);
  x.flags.dropCrfAppend=false;
  const retried=x.savePayloadToSheet_("CRF_30d",corrected,true);
  assert(retried.ok && !retried.existing && retried.record_version===2);
  assert.equal(x.sheets.CRF_30d.rows.length,3);
  assert.equal(x.sheets[CRF_AUDIT_SHEET].rows.length,2);
  console.log("PASS silent CRF write failure blocks success; correction recovers");
}
{
  const x=fakeFixture();
  x.sheets.CRF_30d.rows.push(x.sheets.CRF_30d.rows[1].slice());
  const got=x.savePayloadToSheet_("CRF_30d",fixture,true);
  assert.equal(got.ok,false);
  assert.equal(got.error,"CRF_DUPLICATE_UUID");
  assert.equal(x.sheets[CRF_AUDIT_SHEET].rows.length,1);
  console.log("PASS duplicate CRF UUID is rejected");
}
{
  const x=fakeFixture();
  x.appendByHeaders_(x.sheets[CRF_AUDIT_SHEET],{
    submission_id:fixture.submission_id,sheet_name:"CRF_30d",
    record_key:fixture.record_key,record_version:999,
    registration_id:fixture.registration_id,facility_code:fixture.facility_code,
  });
  const got=x.savePayloadToSheet_("CRF_30d",fixture,true);
  assert(!got.ok && got.error==="CRF_AUDIT_UUID_CONFLICT");
  assert.equal(x.sheets[CRF_AUDIT_SHEET].rows.length,2);
  console.log("PASS audit UUID conflict rejected");
}
{
  const x=fakeFixture(fixture,{auditMissing:true});
  const got=x.savePayloadToSheet_("CRF_30d",fixture,true);
  assert(!got.ok && got.error==="CRF_AUDIT_SHEET_NOT_FOUND");
  console.log("PASS missing audit sheet fails closed");
}

// Validate cross-type UUID isolation under the same logical save lock.
// This is a pure in-memory fixture; the real registration and access checks
// remain in saveCrf_ and must be assessed separately by independent UAT.
{
  const scopeCode=extract("function verifyCrfUuidScope_(", "function savePayloadToSheet_(");
  const x=fakeFixture();
  const scope=new Function(
    "getSpreadsheet_","headerIndex_","CRF_30D_SHEET","CRF_90D_SHEET","CRF_FOLLOWUP_SHEET",
    scopeCode+";return verifyCrfUuidScope_;"
  )(
    ()=>({getSheetByName:name=>x.sheets[name]}),
    h=>Object.fromEntries(h.map((k,i)=>[k,i])),
    "CRF_30d","CRF_90d","CRF_Followup"
  );
  const other={...fixture,crf_type:"day90",visit:"90d"};
  assert.equal(scope("CRF_30d",fixture).ok,true,"same-type UUID replay remains allowed");
  assert.equal(scope("CRF_90d",other).error,"CRF_UUID_CROSS_TYPE_CONFLICT");
  assert.equal(scope("CRF_Followup",other).error,"CRF_UUID_CROSS_TYPE_CONFLICT");
  const newUuid={...other,submission_id:"independent-90d-uuid"};
  assert.equal(scope("CRF_90d",newUuid).ok,true);
  x.sheets.CRF_30d.rows.push(x.sheets.CRF_30d.rows[1].slice());
  assert.equal(scope("CRF_30d",fixture).error,"CRF_DUPLICATE_UUID");
  x.sheets.CRF_90d.rows[0]=x.sheets.CRF_90d.rows[0].filter(k=>k!=="submission_id");
  assert.equal(scope("CRF_90d",newUuid).error,"CRF_UUID_SCHEMA_MISSING");
  console.log("PASS cross-type UUID collision, independent UUID, duplicated row, schema fail-closed");
}

const verifyCode=extract("function validateDay90SourceLink_(payload) {","function draftKey_(");
const verified=(latest)=>new Function("getLatestCrfPayload_","CRF_30D_SHEET",
  verifyCode+"\nreturn validateDay90SourceLink_;"
)((sheet,id,type)=>latest,"CRF_30d");
const original={
  ok:true, found:true, record_version:2,submission_id:"source-2",
  facility_code:"F99",payload:{data:{
    surgery_performed:"実施した",operation_date:"2026-01-13",
  }}
};
const followup={
  registration_id:"JUOG-901",facility_code:"F99",crf_type:"followup",
  data:{
    source_30d_linked:true,source_30d_record_version:2,
    source_30d_submission_id:"source-2",
    surgery_performed:"実施した",reference_date:"2026-01-13",
  }
};
assert(verified(original)(followup).ok);
assert.equal(verified({...original,record_version:3})(followup).error,"SOURCE_CRF_UPDATED");
assert.equal(verified({...original,facility_code:"F98"})(followup).error,"SOURCE_CRF_LINK_MISMATCH");
assert.equal(verified({...original,payload:{data:{surgery_performed:"実施した",operation_date:"2026-01-14"}}})(followup).error,"SOURCE_CRF_LINK_MISMATCH");
assert.equal(verified(original)({...followup,data:{source_30d_linked:false}}).error,"SOURCE_CRF_LINK_REQUIRED");
assert(verified(original)({crf_type:"day90",data:{source_30d_linked:false}}).ok);
console.log("PASS follow-up source linkage / changed reference / manual 90-day");

{
  // Confirm backend_info exposes the exact bound workbook for the pinned
  // Streamlit check. Fictional ID only; no Google API is contacted.
  const infoCode=extract("function getBackendInfo_() {", "// Privacy safeguard:");
  const getBackendInfo=new Function("getSpreadsheet_","BACKEND_VERSION","TIMEZONE","Utilities",
    infoCode+";return getBackendInfo_;"
  )(
    ()=>({getName:()=>"TEST_FICTIONAL_EDC",getId:()=>"isolated-fixture-sheet"}),
    "v2.2.10","Asia/Tokyo",
    {formatDate:()=>"2026-11-16T07:00:00+09:00"}
  );
  const info=getBackendInfo();
  assert.equal(info.ok,true);
  assert.equal(info.backend_version,"v2.2.10");
  assert.equal(info.spreadsheet_id,"isolated-fixture-sheet");
  assert.equal(info.environment,"TEST");
  console.log("PASS authenticated backend workbook binding (fictional)");
}

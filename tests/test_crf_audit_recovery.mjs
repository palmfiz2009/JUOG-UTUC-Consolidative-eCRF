// Real GAS savePayloadToSheet_ plus audit-recovery helpers, in a pure in-memory
// Google Sheets stand-in. No tokens, network, deployed scripts, or patient records.
import fs from "node:fs";
import assert from "node:assert/strict";

const code = fs.readFileSync("05_registry_google_apps_script.gs", "utf8");
const start = code.indexOf("function savePayloadToSheet_(sheetName, payload, enforceVersionRules) {");
const stop = code.indexOf("function submissionExistsInSheet_(sheetName, submissionId) {", start);
assert(start >= 0 && stop > start, "must test the REAL GAS save and audit functions");
const source = code.slice(start, stop);

const CRF_FIELDS = [
  "saved_at", "record_version", "submission_id", "record_key", "submission_kind",
  "correction_reason", "submitted_at", "registration_id", "facility_code",
  "facility_name", "reporter_email", "crf_type", "visit", "schema_version",
  "study_code", "payload_json"
];
const AUDIT_FIELDS = [
  "saved_at", "sheet_name", "record_key", "record_version", "submission_id",
  "submission_kind", "registration_id", "facility_code"
];
const ix = (h, col) => h.indexOf(col);
const headers = h => Object.fromEntries(h.map((name, i) => [name, i]));

function createFixture() {
  const t = {
    CRF_30d: [CRF_FIELDS.slice()],
    CRFSubmissionAudit: [AUDIT_FIELDS.slice()],
  };
  const flags = {
    throwAuditOnce: false, missingAuditReadbackOnce: false,
    corruptCrfAfterAppend: false, suppressCrfReadbackOnce: false,
  };
  const flush = {count:0};
  const sheet = name => ({
    getDataRange() {
      return {getValues: () => {
        if (name === "CRFSubmissionAudit" && flags.missingAuditReadbackOnce &&
            t[name].length > 1) {
          flags.missingAuditReadbackOnce = false;
          return [t[name][0].slice()];
        }
        if (name === "CRF_30d" && flags.suppressCrfReadbackOnce &&
            t[name].length > 1) {
          flags.suppressCrfReadbackOnce = false;
          return [t[name][0].slice()];
        }
        return t[name].map(row => row.slice());
      }};
    },
    appendRow(row) {
      if (name === "CRFSubmissionAudit" && flags.throwAuditOnce) {
        flags.throwAuditOnce = false;
        throw new Error("Fictional injected audit append failure");
      }
      const copy=row.slice();
      if (name==="CRF_30d" && flags.corruptCrfAfterAppend) {
        flags.corruptCrfAfterAppend = false;
        copy[ix(t[name][0], "payload_json")] = "BROKEN_FAKE_PAYLOAD";
      }
      t[name].push(copy);
    },
  });
  const fakeSheet = {
    CRF_30d:sheet("CRF_30d"),
    CRFSubmissionAudit:sheet("CRFSubmissionAudit")
  };
  const deps = {
    getSpreadsheet_:()=>({getSheetByName:n=>fakeSheet[n]||null}),
    headerIndex_:headers,
    ensureDynamicHeaders_:()=>{},
    appendByHeaders_:(sh,obj)=>{
      const rowFields = sh.getDataRange().getValues()[0];
      sh.appendRow(rowFields.map(key=>obj[key]??""));
    },
    flattenObject_:()=>({}),
    CRF_AUDIT_SHEET:"CRFSubmissionAudit",
    SCREENING_CRF_SHEET:"ScreeningCRF",
    SpreadsheetApp:{flush:()=>{flush.count++;}},
  };
  const run = new Function(...Object.keys(deps),source+
    "\nreturn {save:savePayloadToSheet_, audit:ensureCrfAuditRow_, verify:verifySavedCrfRow_};"
  )(...Object.values(deps));
  return {
    t,flags,flush,
    submit:(payload,crf="CRF_30d")=>run.save(crf,payload,true),
    audit:run.audit,
    crfRows:()=>t.CRF_30d.length-1,
    auditRows:()=>t.CRFSubmissionAudit.length-1,
  };
}
const make = (uuid="uuid-fictional-001",kind="初回報告",extra={})=>({
  registration_id:"JUOG-901", facility_code:"TEST01",facility_name:"Fictional QA only",
  reporter_email:"no-email@example.invalid",crf_type:"perioperative_30d", visit:"30d",
  record_key:"JUOG-901|perioperative_30d|30d", submission_id:uuid, submission_kind:kind,
  correction_reason:kind==="訂正報告"?"架空データの訂正":"", submitted_at:"2026-11-15T00:00:00+09:00",
  schema_version:"FICTIONAL", study_code:"JUOG-UTUC01", data:{fictional:true}, ...extra
});
function check(label,fn) {
  fn();
  process.stdout.write("PASS "+label+"\n");
}
check("initial save has CRF v1 and exactly one audit",()=>{
  const f=createFixture(),p=make();
  const a=f.submit(p);
  assert.equal(a.ok,true);assert.equal(a.record_version,1);
  assert.equal(f.crfRows(),1);assert.equal(f.auditRows(),1);
});
check("same uuid replay does not append CRF or audit",()=>{
  const f=createFixture(),p=make();
  f.submit(p);
  const b=f.submit(p);
  assert.equal(b.ok,true);assert.equal(b.existing,true);
  assert.equal(b.record_version,1);assert.equal(f.crfRows(),1);
  assert.equal(f.auditRows(),1);
});
check("missing audit is repaired on same uuid replay",()=>{
  const f=createFixture(),p=make();
  f.submit(p);f.t.CRFSubmissionAudit.splice(1);
  const b=f.submit(p);
  assert.equal(b.ok,true);assert.equal(b.existing,true);
  assert.equal(f.crfRows(),1);assert.equal(f.auditRows(),1);
});
check("audit append failure rejects success; retry repairs with no v2",()=>{
  const f=createFixture(),p=make();
  f.flags.throwAuditOnce=true;
  const a=f.submit(p);
  assert.equal(a.ok,false);assert.equal(a.error,"CRF_AUDIT_UNCONFIRMED");
  assert.equal(f.crfRows(),1);assert.equal(f.auditRows(),0);
  const b=f.submit(p);
  assert.equal(b.ok,true);assert.equal(b.record_version,1);
  assert.equal(f.crfRows(),1);assert.equal(f.auditRows(),1);
});
check("audit disappeared from first readback: fail closed, then replay",()=>{
  const f=createFixture(),p=make();
  f.flags.missingAuditReadbackOnce=true;
  const a=f.submit(p);
  assert.equal(a.ok,false);assert.equal(a.error,"CRF_AUDIT_READBACK_MISSING");
  assert.equal(f.crfRows(),1);assert.equal(f.auditRows(),1);
  const b=f.submit(p);
  assert.equal(b.ok,true);assert.equal(f.auditRows(),1);
});
check("existing audit mismatch refuses success and never creates duplicates",()=>{
  const f=createFixture(),p=make();f.submit(p);
  const row=f.t.CRFSubmissionAudit[1];
  row[ix(f.t.CRFSubmissionAudit[0],"record_version")]=7;
  const a=f.submit(p);
  assert.equal(a.ok,false);assert.equal(a.error,"CRF_AUDIT_UUID_CONFLICT");
  assert.equal(f.crfRows(),1);assert.equal(f.auditRows(),1);
});
check("duplicate audit uuid rejects replay",()=>{
  const f=createFixture(),p=make();f.submit(p);
  f.t.CRFSubmissionAudit.push(f.t.CRFSubmissionAudit[1].slice());
  const a=f.submit(p);
  assert.equal(a.ok,false);assert.equal(a.error,"CRF_AUDIT_DUPLICATE_UUID");
});
check("same uuid with different payload rejected",()=>{
  const f=createFixture(),p=make();f.submit(p);
  const a=f.submit(make(p.submission_id,p.submission_kind,{data:{tampered:true}}));
  assert.equal(a.ok,false);assert.equal(a.error,"SUBMISSION_ID_CONFLICT");
  assert.equal(f.crfRows(),1);assert.equal(f.auditRows(),1);
});
check("same record new initial uuid rejected",()=>{
  const f=createFixture();f.submit(make());
  const a=f.submit(make("uuid-new-initial"));
  assert.equal(a.ok,false);assert.equal(a.error,"INITIAL_ALREADY_EXISTS");
});
check("correction creates v2 and audit v2 only after prior initial",()=>{
  const f=createFixture();f.submit(make());
  const a=f.submit(make("uuid-fictional-002","訂正報告"));
  assert.equal(a.ok,true);assert.equal(a.record_version,2);
  assert.equal(f.crfRows(),2);assert.equal(f.auditRows(),2);
  const b=f.submit(make("uuid-fictional-002","訂正報告"));
  assert.equal(b.ok,true);assert.equal(b.existing,true);
  assert.equal(f.crfRows(),2);assert.equal(f.auditRows(),2);
});
check("first correction without existing report rejected",()=>{
  const f=createFixture();
  const a=f.submit(make("uuid-fake-correction","訂正報告"));
  assert.equal(a.ok,false);assert.equal(a.error,"NO_PRIOR_RECORD_FOR_CORRECTION");
});
check("missing correction reason rejected",()=>{
  const f=createFixture();f.submit(make());
  const a=f.submit(make("uuid-fake-correction","訂正報告",{correction_reason:""}));
  assert.equal(a.ok,false);assert.equal(a.error,"MISSING_CORRECTION_REASON");
});
check("CRF readback content mismatch fails closed, before audit",()=>{
  const f=createFixture(),p=make();
  f.flags.corruptCrfAfterAppend=true;
  const a=f.submit(p);
  assert.equal(a.ok,false);assert.equal(a.error,"CRF_READBACK_CONTENT_MISMATCH");
  assert.equal(f.crfRows(),1);assert.equal(f.auditRows(),0);
});
check("CRF readback absent fails closed, before audit",()=>{
  const f=createFixture(),p=make();
  f.flags.suppressCrfReadbackOnce=true;
  const a=f.submit(p);
  assert.equal(a.ok,false);assert.equal(a.error,"CRF_READBACK_COUNT_MISMATCH");
  assert.equal(f.crfRows(),1);assert.equal(f.auditRows(),0);
});
check("CRF duplicate same UUID rejects without modifying audit",()=>{
  const f=createFixture(),p=make();f.submit(p);
  f.t.CRF_30d.push(f.t.CRF_30d[1].slice());
  const a=f.submit(p);
  assert.equal(a.ok,false);assert.equal(a.error,"CRF_DUPLICATE_SUBMISSION_ID");
  assert.equal(f.auditRows(),1);
});
check("missing required metadata rejects without writes",()=>{
  const f=createFixture(),p=make("", "初回報告");
  const a=f.submit(p);
  assert.equal(a.ok,false);assert.equal(a.error,"MISSING_SUBMISSION_METADATA");
  assert.equal(f.crfRows(),0);assert.equal(f.auditRows(),0);
});
console.log("ALL 16 OFFLINE GCP DATA INTEGRITY CASES PASSED");

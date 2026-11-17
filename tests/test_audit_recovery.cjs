/* Offline integrity tests for Google Apps Script CRF storage.
 * Uses the real script in a Node VM with an in-memory Sheet implementation.
 * No network, Apps Script deployment, email or patient data involved.
 */
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");

class FakeSheet {
  constructor(headers) { this.rows = [[...headers]]; }
  getLastColumn() { return this.rows[0].length; }
  getLastRow() { return this.rows.length; }
  getDataRange() { return { getValues: () => this.rows.map(r => [...r]) }; }
  getRange(r, c, countRows = 1, countCols = 1) {
    return {
      getValues: () => Array.from({length: countRows}, (_, i) =>
        Array.from({length: countCols}, (_, j) =>
          (this.rows[r - 1 + i] || [])[c - 1 + j] ?? "")),
      setValues: values => values.forEach((line, i) => {
        const index = r - 1 + i;
        if (!this.rows[index]) this.rows[index] = [];
        line.forEach((value, j) => { this.rows[index][c - 1 + j] = value; });
      }),
    };
  }
  appendRow(row) { this.rows.push([...row]); }
  asObjects() {
    const headers = this.rows[0];
    return this.rows.slice(1).map(row =>
      Object.fromEntries(headers.map((h, i) => [h, row[i]])));
  }
}
const appScriptPath = path.resolve(__dirname, "..", "05_registry_google_apps_script.gs");
const code = fs.readFileSync(appScriptPath, "utf8");
let workbook;
const context = vm.createContext({
  PropertiesService: { getScriptProperties: () => ({getProperty: () => "offline-synthetic-test"}) },
  SpreadsheetApp: { openById: () => workbook, flush: () => {} },
  Logger: { log: () => {} },
});
vm.runInContext(code, context, { filename: appScriptPath, timeout: 5000 });
function backendConst(expr) { return vm.runInContext(expr, context); }
function fresh() {
  const crf = new FakeSheet(backendConst("CRF_BASE_HEADERS"));
  const audit = new FakeSheet(backendConst("CRF_AUDIT_HEADERS"));
  workbook = {getSheetByName: name => {
    if (name === "CRF_30d") return crf;
    if (name === "CRFSubmissionAudit") return audit;
    throw new Error("Unknown test sheet " + name);
  }};
  return {crf, audit};
}
function p(id, kind = "初回報告", reason = "") {
  return {
    registration_id: "JUOG-999", crf_type: "perioperative_30d", visit: "30d",
    record_key: "JUOG-999|perioperative_30d|30d",
    submission_id: id, submission_kind: kind, correction_reason: reason,
    facility_code: "F11", facility_name: "TEST FACILITY",
    reporter_email: "test@example.invalid", schema_version: "test",
    submitted_at: "2026-11-09T12:00:00+09:00", study_code: "JUOG_TEST",
    data: {surgery_performed: "実施しなかった"},
  };
}
let passed = 0;
function check(name, fn) {
  try { fn(); console.log("PASS " + name); passed++; }
  catch (e) { console.error("FAIL " + name + ": " + e.stack); process.exitCode = 1; }
}
check("initial report creates version 1 and identical audit linkage", () => {
  const {crf, audit} = fresh();
  const first = p("SYNTHETIC-INITIAL-1");
  const result = context.savePayloadToSheet_("CRF_30d", first, true);
  assert.equal(result.ok, true);
  assert.equal(result.record_version, 1);
  assert.equal(crf.rows.length, 2);
  assert.equal(audit.rows.length, 2);
  assert.equal(audit.asObjects()[0].submission_id, first.submission_id);
  assert.equal(audit.asObjects()[0].record_version, 1);
  assert.equal(crf.asObjects()[0].record_key, first.record_key);
});
check("same initial submission is idempotent; new initial ID rejected", () => {
  const {crf, audit} = fresh();
  const first = p("SYNTHETIC-1");
  context.savePayloadToSheet_("CRF_30d", first, true);
  const again = context.savePayloadToSheet_("CRF_30d", first, true);
  assert.equal(again.ok, true);
  assert.equal(again.existing, true);
  const rejected = context.savePayloadToSheet_("CRF_30d", p("SYNTHETIC-2"), true);
  assert.equal(rejected.ok, false);
  assert.equal(rejected.error, "INITIAL_ALREADY_EXISTS");
  assert.equal(crf.rows.length, 2);
  assert.equal(audit.rows.length, 2);
});
check("correction appends version 2 preserving initial row", () => {
  const {crf, audit} = fresh();
  context.savePayloadToSheet_("CRF_30d", p("SYNTHETIC-1"), true);
  const corrected = p("SYNTHETIC-2", "訂正報告", "Synthetic UAT correction");
  const result = context.savePayloadToSheet_("CRF_30d", corrected, true);
  assert.equal(result.ok, true);
  assert.equal(result.record_version, 2);
  assert.equal(crf.rows.length, 3);
  assert.equal(audit.rows.length, 3);
  assert.deepEqual(crf.asObjects().map(r => r.record_version), [1, 2]);
  assert.deepEqual(audit.asObjects().map(r => r.record_version), [1, 2]);
  assert.deepEqual(audit.asObjects().map(r => r.submission_id),
    ["SYNTHETIC-1", "SYNTHETIC-2"]);
});
check("invalid correction or mismatched key is rejected without writing", () => {
  const {crf, audit} = fresh();
  assert.equal(context.savePayloadToSheet_("CRF_30d",
    p("NO-PRIOR", "訂正報告", "test"), true).error,
    "NO_PRIOR_RECORD_FOR_CORRECTION");
  const malformed = p("BAD-KEY");
  malformed.record_key = "JUOG-888|perioperative_30d|30d";
  assert.equal(context.savePayloadToSheet_("CRF_30d", malformed, true).error,
    "RECORD_KEY_MISMATCH");
  context.savePayloadToSheet_("CRF_30d", p("SYNTHETIC-1"), true);
  assert.equal(context.savePayloadToSheet_("CRF_30d",
    p("MISSING-REASON", "訂正報告"), true).error,
    "MISSING_CORRECTION_REASON");
  assert.equal(crf.rows.length, 2);
  assert.equal(audit.rows.length, 2);
});
check("conflicting reuse of submission ID fails closed", () => {
  const {crf, audit} = fresh();
  context.savePayloadToSheet_("CRF_30d", p("SYNTHETIC-1"), true);
  const tampered = p("SYNTHETIC-1");
  tampered.data.surgery_performed = "実施した";
  const result = context.savePayloadToSheet_("CRF_30d", tampered, true);
  assert.equal(result.error, "SUBMISSION_ID_CONFLICT");
  assert.equal(crf.rows.length, 2);
  assert.equal(audit.rows.length, 2);
});
check("cN1 cap counts only cT<=3 cN1 cM0", () => {
  assert.equal(context.isCn1Only_("cT3", "cN1", "cM0"), true);
  assert.equal(context.isCn1Only_("cT4", "cN1", "cM0"), false);
  assert.equal(context.isCn1Only_("cT3", "cN1", "cM1"), false);
  assert.equal(context.isCn1Only_("cT3", "cN2", "cM0"), false);
  assert.equal(context.isCn1Only_("cT1", "cN1", "cM0"), true);
});
check("direct patient identifiers rejected recursively", () => {
  assert.equal(context.containsDirectIdentifier_({data: {patient_name: "TEST"}}), true);
  assert.equal(context.containsDirectIdentifier_({data: {MRN: "TEST"}}), true);
  assert.equal(context.containsDirectIdentifier_({data: {stage: "cT3"}}), false);
});

check("role-gated actions reject missing or wrong-role credentials", () => {
  const props = {getProperty: key => ({
    JUOG_ADMIN_ACTION_TOKEN: "TEST_ADMIN_ONLY",
    JUOG_REVIEWER_RADIOLOGY_ACTION_TOKEN: "TEST_RADIOLOGY_ONLY",
  }[key] || "")};
  assert.equal(context.authorizeJuogAction_("list_screenings", null, {}, props).error,
    "ROLE_AUTH_REQUIRED");
  assert.equal(context.authorizeJuogAction_("list_screenings",
    {kind:"reviewer",role:"radiology",key:"TEST_RADIOLOGY_ONLY"}, {}, props).error,
    "ROLE_NOT_ALLOWED");
  assert.equal(context.authorizeJuogAction_("list_screenings",
    {kind:"admin",key:"INVALID"}, {}, props).error,
    "ROLE_AUTH_FAILED");
  assert.equal(context.authorizeJuogAction_("list_screenings",
    {kind:"admin",key:"TEST_ADMIN_ONLY"}, {}, props).ok, true);
  assert.equal(context.authorizeJuogAction_("get_own_review",
    {kind:"reviewer",role:"radiology",key:"TEST_RADIOLOGY_ONLY"},
    {reviewer_role:"urology"}, props).error, "REVIEWER_ROLE_MISMATCH");
});
check("reviewer response hides other reviewers' clinical judgments", () => {
  const result = context.reviewerMdtProgressOnly_({
    ok:true, screening_id:"JUOG-SCR-999", review_round:1,
    required:3, completed:1, all_complete:false,
    reviews:{radiology:{decision:"ELIGIBLE",central_recist:"PR"},
      urology:null,medical_oncology:null},
  });
  assert.equal(result.ok, true);
  assert.equal(result.reviews.radiology.submitted, true);
  assert.equal(result.reviews.urology, null);
  assert.equal(JSON.stringify(result).includes("ELIGIBLE"), false);
  assert.equal(JSON.stringify(result).includes("central_recist"), false);
});
check("cN1-only registered counting excludes cT4 and cM1, fails closed if unverifiable", () => {
  const rIdx={registration_id:0,cN:1,screening_id:2};
  const sIdx={screening_id:0,cT:1,cN:2,cM:3};
  const activeRows=[
    ["JUOG-901","cN1","JUOG-SCR-901"],
    ["JUOG-902","cN1","JUOG-SCR-902"],
    ["JUOG-903","cN1","JUOG-SCR-903"],
    ["JUOG-904","cN0","JUOG-SCR-904"],
  ];
  const screened=[
    ["screening_id","cT","cN","cM"],
    ["JUOG-SCR-901","cT3","cN1","cM0"],
    ["JUOG-SCR-902","cT4","cN1","cM0"],
    ["JUOG-SCR-903","cT3","cN1","cM1"],
    ["JUOG-SCR-904","cT3","cN0","cM0"],
  ];
  assert.equal(context.countCn1OnlyRegistered_(activeRows,rIdx,screened,sIdx),1);
  assert.throws(() => context.countCn1OnlyRegistered_(
    [["JUOG-905","cN1","JUOG-SCR-MISSING"]],rIdx,screened,sIdx),
    /CN1_ONLY_COUNT_UNVERIFIABLE/);
});


check("audit append failure is repaired by SAME submission ID retry", () => {
  const {crf, audit} = fresh();
  const first = p("TEST-AUDIT-RECOVERY-1");
  const normalAppend = audit.appendRow.bind(audit);
  audit.appendRow = () => { throw new Error("SIMULATED_AUDIT_APPEND_FAILURE"); };
  assert.throws(() => context.savePayloadToSheet_("CRF_30d", first, true),
    /SIMULATED_AUDIT_APPEND_FAILURE/);
  assert.equal(crf.rows.length, 2, "CRF already saved before failed audit");
  assert.equal(audit.rows.length, 1, "audit entry not written");
  audit.appendRow = normalAppend;
  const retried = context.savePayloadToSheet_("CRF_30d", first, true);
  assert.equal(retried.ok, true);
  assert.equal(retried.existing, true);
  assert.equal(retried.audit_repaired, true);
  assert.equal(retried.record_version, 1);
  assert.equal(crf.rows.length, 2, "original CRF must not be duplicated");
  assert.equal(audit.rows.length, 2, "one audit record must be repaired");
  assert.equal(audit.asObjects()[0].submission_id, first.submission_id);
  const repeated = context.savePayloadToSheet_("CRF_30d", first, true);
  assert.equal(repeated.ok, true);
  assert.equal(repeated.audit_repaired, false);
  assert.equal(audit.rows.length, 2, "replay must not create audit duplicate");
});
check("audit repair also works for correction version 2", () => {
  const {crf, audit} = fresh();
  context.savePayloadToSheet_("CRF_30d", p("TEST-V1"), true);
  const correction = p("TEST-V2", "訂正報告", "synthetic correction");
  const normalAppend = audit.appendRow.bind(audit);
  audit.appendRow = () => { throw new Error("SIMULATED_AUDIT_APPEND_FAILURE"); };
  assert.throws(() => context.savePayloadToSheet_("CRF_30d", correction, true),
    /SIMULATED_AUDIT_APPEND_FAILURE/);
  assert.equal(crf.rows.length, 3);
  assert.equal(audit.rows.length, 2);
  audit.appendRow = normalAppend;
  const retried = context.savePayloadToSheet_("CRF_30d", correction, true);
  assert.equal(retried.ok, true);
  assert.equal(retried.record_version, 2);
  assert.equal(retried.audit_repaired, true);
  assert.deepEqual(crf.asObjects().map(r => r.record_version), [1, 2]);
  assert.deepEqual(audit.asObjects().map(r => r.record_version), [1, 2]);
});
check("conflicting audit record fails closed without duplicate", () => {
  const {crf, audit} = fresh();
  const payload = p("TEST-CONFLICT");
  context.savePayloadToSheet_("CRF_30d", payload, true);
  const id = audit.rows[0].indexOf("facility_code");
  audit.rows[1][id] = "DIFFERENT_FACILITY";
  const retried = context.savePayloadToSheet_("CRF_30d", payload, true);
  assert.equal(retried.ok, false);
  assert.equal(retried.error, "CRF_AUDIT_CONFLICT");
  assert.equal(crf.rows.length, 2);
  assert.equal(audit.rows.length, 2);
});
check("missing audit sheet is rejected before saving new CRF", () => {
  const {crf, audit} = fresh();
  const originalGet = workbook.getSheetByName.bind(workbook);
  workbook.getSheetByName = name => name === "CRFSubmissionAudit" ? null : originalGet(name);
  const result = context.savePayloadToSheet_("CRF_30d", p("TEST-MISSING-SHEET"), true);
  assert.equal(result.ok, false);
  assert.equal(result.error, "CRF_AUDIT_SHEET_MISSING");
  assert.equal(crf.rows.length, 1, "do not append CRF if audit sheet missing");
  assert.equal(audit.rows.length, 1);
});

console.log("Completed: " + passed + "/14 offline backend contract checks.");
if (passed !== 14) process.exitCode = 1;

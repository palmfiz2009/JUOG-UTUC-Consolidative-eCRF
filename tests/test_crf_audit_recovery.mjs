// Real GAS savePayloadToSheet_ plus audit-recovery helpers, in a pure in-memory
// Google Sheets stand-in. No tokens, network, deployed scripts, or patient records.
import fs from "node:fs";
import assert from "node:assert/strict";

const code = fs.readFileSync("05_registry_google_apps_script.gs", "utf8");
const start = code.indexOf("function savePayloadToSheet_(sheetName, payload, enforceVersionRules) {");
const stop = code.indexOf("function submissionExistsInSheet_(sheetName, submissionId) {", start);
assert(start >= 0 && stop > start, "must test the REAL GAS save and audit functions");
const source = code.slice(start, stop);
const privacyStart = code.indexOf("function directIdentifierKey_(key) {");
const privacyStop = code.indexOf("function isCn1Only_(cT, cN, cM) {",privacyStart);
assert(privacyStart > 0 && privacyStop > privacyStart,"integrated AUTH-04 privacy guard required");
const containsDirectIdentifier = new Function(
  code.slice(privacyStart,privacyStop)+"\nreturn containsDirectIdentifier_;"
)();


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
  const sourceEvents = [];
  flags.lockHeld = false;
  flags.blockSource = false;
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
    validateDay90SourceLink_:()=>{
      sourceEvents.push(Boolean(flags.lockHeld));
      return flags.blockSource ? {ok:false, error:"SOURCE_VERSION_CHANGED"} : {ok:true};
    },
    CRF_AUDIT_SHEET:"CRFSubmissionAudit",
    SCREENING_CRF_SHEET:"ScreeningCRF",
    SpreadsheetApp:{flush:()=>{flush.count++;}},
  };
  const run = new Function(...Object.keys(deps),source+
    "\nreturn {save:savePayloadToSheet_, audit:ensureCrfAuditRow_, verify:verifySavedCrfRow_};"
  )(...Object.values(deps));
  const crfSourceStart = code.indexOf("function saveCrf_(p) {");
  assert(crfSourceStart >= 0 && crfSourceStart < start);
  const crfSource = code.slice(crfSourceStart, start);
  const saveDeps = {
    containsDirectIdentifier_:containsDirectIdentifier,
    crfSheetForType_:()=> "CRF_30d",
    validateSubject_:()=>({ok:true}),
    validateCrfHardStops_:()=>({ok:true}),
    LockService:{getScriptLock:()=>({
      tryLock:()=>{flags.lockHeld=true; return true},
      releaseLock:()=>{flags.lockHeld=false}
    })},
    savePayloadToSheet_:run.save,
  };
  const actualSaveCrf = new Function(...Object.keys(saveDeps),crfSource+
    "\nreturn saveCrf_;"
  )(...Object.values(saveDeps));
  return {
    t,flags,flush,sourceEvents,
    submit:(payload,crf="CRF_30d")=>run.save(crf,payload,true),
    saveCrf:payload=>actualSaveCrf({payload}),
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
check("new linked CRF validated while ScriptLock is held",()=>{
  const f=createFixture(),p=make();
  const res=f.saveCrf(p);
  assert.equal(res.ok,true);
  assert.deepEqual(f.sourceEvents,[true]);
  assert.equal(f.flags.lockHeld,false);
});
check("stale source rejected under lock, but same UUID replay bypasses fresh check",()=>{
  const f=createFixture(),p=make();
  f.flags.blockSource=true;
  const before=f.saveCrf(p);
  assert.equal(before.ok,false);assert.equal(before.error,"SOURCE_VERSION_CHANGED");
  assert.equal(f.crfRows(),0);assert.equal(f.flags.lockHeld,false);
  f.flags.blockSource=false;
  const saved=f.saveCrf(p);
  assert.equal(saved.ok,true);assert.equal(f.crfRows(),1);
  f.flags.blockSource=true;
  const replay=f.saveCrf(p);
  assert.equal(replay.ok,true);assert.equal(replay.existing,true);
  assert.equal(f.crfRows(),1);assert.equal(f.auditRows(),1);
  assert.deepEqual(f.sourceEvents,[true,true]);
});
check("integrated: direct identifier is blocked before CRF/audit write",()=>{
  const f=createFixture();
  const forbidden=make("fictional-privacy-denial","初回報告",{
    data:{reg_birth_date:{type:"date",value:"1980-01-02"}}
  });
  const a=f.saveCrf(forbidden);
  assert.equal(a.ok,false);
  assert.equal(a.error,"DIRECT_IDENTIFIER_NOT_ALLOWED");
  assert.equal(f.crfRows(),0);assert.equal(f.auditRows(),0);
  assert.deepEqual(f.sourceEvents,[]);
  assert.equal(f.flags.lockHeld,false);
});
check("integrated: permitted clinical date writes once with verified audit",()=>{
  const f=createFixture(),p=make("fictional-clinical-date","初回報告",{
    data:{consent_date:"2026-11-01",birth_year_month:"1980-01",age_at_consent:46}
  });
  const a=f.saveCrf(p);
  assert.equal(a.ok,true);assert.equal(a.record_version,1);
  assert.equal(f.crfRows(),1);assert.equal(f.auditRows(),1);
});
check("integrated: allowed payload audit failure restores on same-UUID replay",()=>{
  const f=createFixture(),p=make("fictional-retry-after-audit-error");
  f.flags.throwAuditOnce=true;
  const a=f.saveCrf(p);
  assert.equal(a.ok,false);assert.equal(a.error,"CRF_AUDIT_UNCONFIRMED");
  assert.equal(f.crfRows(),1);assert.equal(f.auditRows(),0);
  const b=f.saveCrf(p);
  assert.equal(b.ok,true);assert.equal(b.existing,true);
  assert.equal(b.record_version,1);
  assert.equal(f.crfRows(),1);assert.equal(f.auditRows(),1);
});
check("lost-browser replay with new UUID and identical correction does not create v3",()=>{
  const f=createFixture();
  assert.equal(f.saveCrf(make()).ok,true);
  assert.equal(f.saveCrf(make("corr-v2","訂正報告",{data:{test:"corrected"}})).ok,true);
  const repeat=make("new-client-uuid","訂正報告",{
    data:{test:"corrected"},submitted_at:"2026-11-16T07:00:00+09:00"
  });
  const response=f.saveCrf(repeat);
  assert.equal(response.ok,false);
  assert.equal(response.error,"DUPLICATE_CONTENT_ALREADY_RECORDED");
  assert.equal(response.record_version,2);
  assert.equal(f.crfRows(),2);assert.equal(f.auditRows(),2);
});
check("changed correction content is a genuinely new v3 with audited history",()=>{
  const f=createFixture();
  f.saveCrf(make());
  f.saveCrf(make("corr-v2","訂正報告",{data:{test:"corrected"}}));
  const next=f.saveCrf(make("corr-v3","訂正報告",{data:{test:"changed again"}}));
  assert.equal(next.ok,true);assert.equal(next.record_version,3);
  assert.equal(f.crfRows(),3);assert.equal(f.auditRows(),3);
});
check("missing prior audit blocks new correction before any write",()=>{
  const f=createFixture(),original=make();
  f.saveCrf(original);
  f.t.CRFSubmissionAudit.splice(1,1);
  const next=f.saveCrf(make("new-correction","訂正報告",{data:{test:"new"}}));
  assert.equal(next.ok,false);assert.equal(next.error,"PREVIOUS_CRF_AUDIT_UNCONFIRMED");
  assert.equal(f.crfRows(),1);assert.equal(f.auditRows(),0);
  const recovered=f.saveCrf(original);
  assert.equal(recovered.ok,true);assert.equal(recovered.existing,true);
  const ready=f.saveCrf(make("new-correction","訂正報告",{data:{test:"new"}}));
  assert.equal(ready.ok,true);assert.equal(ready.record_version,2);
  assert.equal(f.crfRows(),2);assert.equal(f.auditRows(),2);
});
check("tampered previous audit blocks duplicate-content error and new version",()=>{
  const f=createFixture();
  f.saveCrf(make());f.saveCrf(make("corr-v2","訂正報告",{data:{test:1}}));
  f.t.CRFSubmissionAudit[2][ix(f.t.CRFSubmissionAudit[0],"record_version")]=12;
  const r=f.saveCrf(make("new-uuid","訂正報告",{data:{test:1}}));
  assert.equal(r.ok,false);assert.equal(r.error,"PREVIOUS_CRF_AUDIT_UNCONFIRMED");
  assert.equal(f.crfRows(),2);assert.equal(f.auditRows(),2);
});
check("corrupt or ambiguous version history blocks any further correction",()=>{
  const f=createFixture();f.saveCrf(make());f.saveCrf(make("corr-v2","訂正報告",{data:{a:1}}));
  f.t.CRF_30d[2][ix(f.t.CRF_30d[0],"record_version")]=1;
  const r=f.saveCrf(make("corr-v3","訂正報告",{data:{a:2}}));
  assert.equal(r.ok,false);assert.equal(r.error,"PREVIOUS_CRF_HISTORY_INCONSISTENT");
  assert.equal(f.crfRows(),2);assert.equal(f.auditRows(),2);
});
check("different serialized field order is not a new correction version",()=>{
  const f=createFixture();f.saveCrf(make());
  f.saveCrf(make("corr-v2","訂正報告",{data:{first:"A",second:"B"}}));
  const duplicate=f.saveCrf(make("corr-new","訂正報告",{data:{second:"B",first:"A"}}));
  assert.equal(duplicate.ok,false);
  assert.equal(duplicate.error,"DUPLICATE_CONTENT_ALREADY_RECORDED");
  assert.equal(f.crfRows(),2);assert.equal(f.auditRows(),2);
});
console.log("ALL 27 OFFLINE INTEGRATED GCP DATA INTEGRITY CASES PASSED");

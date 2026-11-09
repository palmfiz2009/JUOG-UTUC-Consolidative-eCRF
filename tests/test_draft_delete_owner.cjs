/* Verify CRF draft deletion ownership using real Apps Script functions.
 * Synthetic in-memory only: no deployed Google Apps Script or network.
 */
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const source = fs.readFileSync(path.resolve(__dirname, "..", "05_registry_google_apps_script.gs"), "utf8");
const ctx = vm.createContext({
  Logger: {log() {}},
  SpreadsheetApp: {flush() {}},
  LockService: {getScriptLock: () => ({tryLock: () => true, releaseLock() {}})},
  Utilities: {formatDate: () => "2026-11-09T00:00:00+09:00"}
});
vm.runInContext(source, ctx, {timeout: 5000});

class FakeSheet {
  constructor(headers) {
    this.rows = [Array.from(headers)];
    this.deleted = [];
  }
  getLastRow() { return this.rows.length; }
  getLastColumn() { return this.rows[0].length; }
  getDataRange() { return {getValues: () => this.rows.map(x=>x.slice())}; }
  getRange(row, col, height=1, width=1) {
    return {
      getValues: () => Array.from({length:height}, (_,i) =>
        Array.from({length:width},(_,j) => (this.rows[row-1+i] || [])[col-1+j]??"")),
      setValues: v => v.forEach((r,i) => {
        const line=this.rows[row-1+i]||[];
        r.forEach((val,j)=>{line[col-1+j]=val;});
        this.rows[row-1+i]=line;
      })
    };
  }
  appendRow(data) {this.rows.push(data.slice());}
  setFrozenRows() {}
  deleteRow(row) {this.deleted.push(row);this.rows.splice(row-1,1);}
}
const draft = new FakeSheet(vm.runInContext("CRF_DRAFT_HEADERS",ctx));
ctx.testWorkbook={getSheetByName:(name)=>name==="CRF_Drafts"?draft:null};
vm.runInContext("getSpreadsheet_ = function(){return testWorkbook;}; validateSubject_ = function(p){return p.registration_id === 'JUOG-999' ? {ok:true,facility_code:'F11',facility_name:'TEST'} : {ok:false,error:'SUBJECT_NOT_FOUND'};};",ctx);

function addDraft(owner="owner@example.invalid", key="JUOG-999|perioperative_30d|30d") {
  const item={draft_key:key, registration_id:"JUOG-999",
    crf_type:"perioperative_30d", visit:"30d",
    facility_code:"F11", facility_name:"TEST",
    reporter_email:owner, draft_json:'{"peri_lab_Hb":"12.7"}'};
  draft.appendRow(draft.rows[0].map(h=>item[h]??""));
}
function request(email, opts={}) {
  return ctx.deleteDraft_({registration_id:"JUOG-999",
    crf_type:opts.crf_type||"perioperative_30d",
    visit:opts.visit||"30d", reporter_email:email});
}
let pass=0;
function check(name,fn) {
  try {fn();pass++;console.log("PASS "+name);}
  catch(e){console.error("FAIL "+name, e.stack);process.exitCode=1;}
}
check("deletion without email is refused before draft read",()=>{
  draft.rows.splice(1);
  addDraft();
  const result=request("");
  assert.equal(result.error,"INVALID_DRAFT_EMAIL");
  assert.equal(draft.getLastRow(),2);
  assert.deepEqual(draft.deleted,[]);
});
check("other reporter cannot delete saved draft",()=>{
  assert.equal(request("other@example.invalid").error,"DRAFT_EMAIL_MISMATCH");
  assert.equal(draft.getLastRow(),2);
});
check("only matching normalized owner can delete its draft",()=>{
  const result=request(" OWNER@EXAMPLE.INVALID ");
  assert.equal(result.ok,true);
  assert.equal(result.deleted,true);
  assert.equal(draft.getLastRow(),1);
});
check("retry after deletion is safe and idempotent",()=>{
  const result=request("owner@example.invalid");
  assert.equal(result.ok,true);
  assert.equal(result.deleted,false);
});
check("visit key isolation prevents adjacent visit deletion",()=>{
  addDraft("owner@example.invalid","JUOG-999|followup|6m");
  addDraft("owner@example.invalid","JUOG-999|followup|9m");
  const result=request("owner@example.invalid",{crf_type:"followup",visit:"6m"});
  assert.equal(result.ok,true);
  assert.equal(draft.getLastRow(),2);
  assert.equal(draft.rows[1][draft.rows[0].indexOf("draft_key")],
    "JUOG-999|followup|9m");
});
check("unrelated study ID cannot delete draft",()=>{
  const result=ctx.deleteDraft_({registration_id:"JUOG-555",
    crf_type:"followup",visit:"9m",reporter_email:"owner@example.invalid"});
  assert.equal(result.error,"SUBJECT_NOT_FOUND");
  assert.equal(draft.getLastRow(),2);
});
check("draft with unset owner cannot be deleted",()=>{
  const index=draft.rows[0].indexOf("reporter_email");
  draft.rows[1][index]="";
  const result=request("owner@example.invalid",{crf_type:"followup",visit:"9m"});
  assert.equal(result.error,"DRAFT_EMAIL_NOT_SET");
  assert.equal(draft.getLastRow(),2);
});

ctx.screeningDraftId_ = (facility,code) => "PREMDT-" + facility + "-" + code;
function addScreeningDraft(owner="owner@example.invalid", facility="F11", code="LOCAL-999"){
  const draftKey=ctx.screeningDraftId_(facility,code)+"|screening|mdt_application";
  const item={draft_key:draftKey,registration_id:ctx.screeningDraftId_(facility,code),
    crf_type:"screening",visit:"mdt_application",facility_code:facility,
    reporter_email:owner,draft_json:'{"synthetic":true}'};
  draft.appendRow(draft.rows[0].map(h=>item[h]??""));
}
function removeScreening(email,facility="F11",code="LOCAL-999"){
  return ctx.deleteScreeningDraft_({facility_code:facility,
    local_subject_code:code,reporter_email:email});
}
check("pre-MDT delete without reporter email is rejected",()=>{
  draft.rows.splice(1);addScreeningDraft();
  assert.equal(removeScreening("").error,"INVALID_DRAFT_EMAIL");
  assert.equal(draft.getLastRow(),2);
});
check("pre-MDT another reporter cannot delete screening draft",()=>{
  assert.equal(removeScreening("other@example.invalid").error,"DRAFT_EMAIL_MISMATCH");
  assert.equal(draft.getLastRow(),2);
});
check("pre-MDT correct owner removes only its one screening draft",()=>{
  addScreeningDraft("owner@example.invalid","F11","LOCAL-998");
  const result=removeScreening(" OWNER@EXAMPLE.INVALID ");
  assert.equal(result.ok,true);
  assert.equal(result.deleted,true);
  assert.equal(draft.getLastRow(),2);
  assert.equal(draft.rows[1][draft.rows[0].indexOf("draft_key")],
    "PREMDT-F11-LOCAL-998|screening|mdt_application");
});
check("pre-MDT repeated delete is idempotent and other site key is isolated",()=>{
  addScreeningDraft("owner@example.invalid","F12","LOCAL-999");
  const repeat=removeScreening("owner@example.invalid");
  assert.equal(repeat.ok,true);
  assert.equal(repeat.deleted,false);
  const other=removeScreening("owner@example.invalid","F12","LOCAL-999");
  assert.equal(other.ok,true);
  assert.equal(other.deleted,true);
  assert.equal(draft.getLastRow(),2);
});
check("pre-MDT draft with no owner fails closed",()=>{
  const emailIndex=draft.rows[0].indexOf("reporter_email");
  draft.rows[1][emailIndex]="";
  const result=removeScreening("owner@example.invalid","F11","LOCAL-998");
  assert.equal(result.error,"DRAFT_EMAIL_NOT_SET");
  assert.equal(draft.getLastRow(),2);
});
console.log("Completed "+pass+"/12 isolated draft ownership tests.");
if(pass!==12)process.exitCode=1;

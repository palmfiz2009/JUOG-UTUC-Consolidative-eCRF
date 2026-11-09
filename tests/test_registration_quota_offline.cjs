/* JUOG-UTUC01: offline quota regression against real candidate GAS source.
 * No network, credentials, Script Properties or actual Google Sheet writes.
 * Run: node tests/test_registration_quota_offline.cjs
 */
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "..", "05_registry_google_apps_script.gs"), "utf8");
let releaseCount = 0;
const ctx = vm.createContext({
  Logger: { log() {} },
  Utilities: {
    formatDate(value, zone, format) {
      assert.equal(zone, "Asia/Tokyo");
      if (format === "yyyy-MM-dd") return "2026-11-09";
      return new Date(value).toISOString();
    }
  },
  SpreadsheetApp: { flush() {} },
  LockService: {
    getScriptLock() {
      return { tryLock() { return true; }, releaseLock() { releaseCount++; } };
    }
  }
});
vm.runInContext(source, ctx, { timeout: 10000 });
const regHeaders = Array.from(vm.runInContext("REGISTRY_HEADERS", ctx));
const screenHeaders = Array.from(vm.runInContext("SCREENING_HEADERS", ctx));
const auditHeaders = Array.from(vm.runInContext("SCREENING_AUDIT_HEADERS", ctx));
const indexes = headers => Object.fromEntries(headers.map((h, i) => [h, i]));
const regIdx = indexes(regHeaders), screenIdx = indexes(screenHeaders);
const mkrow = (headers, obj) => headers.map(k => obj[k] ?? "");
let passed = 0;
function check(name, fn) {
  fn();
  passed++;
  console.log("PASS " + name);
}
function isOnly(cT, cN, cM) { return ctx.isCn1Only_(cT, cN, cM); }
[
  ["cTa,N1,M0", "cTa", "cN1", "cM0", true],
  ["cTis,N1,M0", "cTis", "cN1", "cM0", true],
  ["cT1,N1,M0", "cT1", "cN1", "cM0", true],
  ["cT3,N1,M0", "cT3", "cN1", "cM0", true],
  ["cT4,N1,M0 excluded", "cT4", "cN1", "cM0", false],
  ["cT3,N1,M1 excluded", "cT3", "cN1", "cM1", false],
  ["cT4,N1,M1 excluded", "cT4", "cN1", "cM1", false],
  ["cT3,N2,M0 excluded", "cT3", "cN2", "cM0", false],
  ["cT3,N0,M0 excluded", "cT3", "cN0", "cM0", false]
].forEach(([label, cT, cN, cM, expected]) => check(label, () => assert.equal(isOnly(cT,cN,cM),expected)));

function prepare({ cn1 = 0, sd = 0, extra = 0, target = {}, settings = {} } = {}) {
  const regRows = [regHeaders];
  const screenRows = [screenHeaders];
  const targetRow = mkrow(screenHeaders, {
    screening_id:"JUOG-SCR-999", review_round:1, status:"PENDING",
    cT:"cT3", cN:"cN1", cM:"cM0", best_effect:"PR",
    facility_code:"TEST", facility_name:"架空試験施設",
    local_subject_code:"SYNTHETIC-TARGET", site_recist:"PR",
    planned_surgery_date:"2026-12-01", ...target
  });
  screenRows.push(targetRow);
  for (let i=0; i<cn1+sd+extra; i++) {
    const isCn1 = i < cn1;
    const isSd = i >= cn1 && i < cn1+sd;
    const screeningId="JUOG-SCR-"+String(i+1).padStart(3,"0");
    const state = {screening_id:screeningId, cT:isCn1?"cT3":"cT4",
      cN:isCn1?"cN1":"cN0", cM:"cM0", status:"REGISTERED", review_round:1};
    screenRows.push(mkrow(screenHeaders,state));
    regRows.push(mkrow(regHeaders,{registration_id:"JUOG-"+String(i+1).padStart(3,"0"),
      status:"ACTIVE", facility_code:"TEST", local_subject_code:"EXISTING-"+i,
      screening_id:screeningId, cN:state.cN, best_effect:isSd?"SD":"PR"}));
  }
  let writes = 0;
  const sheets = {
    Registry: {headers:regHeaders,rows:regRows},
    Screening: {headers:screenHeaders,rows:screenRows},
    ScreeningAudit: {headers:auditHeaders,rows:[auditHeaders]}
  };
  for(const sh of Object.values(sheets)){
    sh.getDataRange = () => ({getValues:()=>sh.rows});
  }
  const store = {getSheetByName: name => {
    if(!sheets[name]) throw Error("Unexpected sheet: "+name);
    return sheets[name];
  }};
  ctx.getSpreadsheet_ = () => store;
  ctx.findScreening_ = id => id==="JUOG-SCR-999"
    ? {row:targetRow,idx:screenIdx,values:screenRows,sheetRow:2} : null;
  ctx.latestReview_ = (sid, round, role) => {
    if(sid!=="JUOG-SCR-999" || round!==1) return null;
    return {decision:"ELIGIBLE", central_recist:role==="radiology"?"PR":""};
  };
  ctx.getSettings_ = () => ({
    TOTAL_MAX:"42", ALLOW_TOTAL_AFTER_MAX:"FALSE",
    CN1_MAX:"20", SD_HOLD_THRESHOLD:"12",
    ALLOW_SD_AFTER_THRESHOLD:"FALSE", ...settings
  });
  ctx.appendByHeaders_ = (sh,obj) => {
    writes++;
    sh.rows.push(mkrow(sh.headers,obj));
  };
  ctx.setByHeader_ = (sh,rowIndex,idx,obj) => {
    writes++;
    for(const [key,value] of Object.entries(obj))
      if(idx[key]!==undefined) sh.rows[rowIndex-1][idx[key]]=value;
  };
  return {get writes(){return writes;}, sheets,screenRows,regRows};
}
function finalize(env) {
  const before = releaseCount;
  const response = ctx.finalizeMdt_({
    screening_id:"JUOG-SCR-999",decision:"ELIGIBLE",
    mdt_date:"2026-11-09",admin_user:"UAT-SYNTHETIC",
    consensus_confirmed:true
  });
  assert.equal(releaseCount,before+1,"ScriptLock must be released");
  return response;
}
check("CN1 counter includes only cT<=3 cN1 M0",()=>{
  const e=prepare({cn1:1});
  e.screenRows.push(mkrow(screenHeaders,{screening_id:"JUOG-SCR-010",cT:"cT4",cN:"cN1",cM:"cM0"}));
  e.regRows.push(mkrow(regHeaders,{registration_id:"JUOG-010",status:"ACTIVE",screening_id:"JUOG-SCR-010",cN:"cN1"}));
  e.screenRows.push(mkrow(screenHeaders,{screening_id:"JUOG-SCR-011",cT:"cT3",cN:"cN1",cM:"cM1"}));
  e.regRows.push(mkrow(regHeaders,{registration_id:"JUOG-011",status:"ACTIVE",screening_id:"JUOG-SCR-011",cN:"cN1"}));
  assert.equal(ctx.countCn1OnlyRegistered_(e.regRows.slice(1),regIdx,e.screenRows,screenIdx),1);
});
check("CN1 count fails closed when a registered cN1 lacks linked screening",()=>{
  const e=prepare({cn1:1});
  e.screenRows.pop();
  assert.throws(()=>ctx.countCn1OnlyRegistered_(e.regRows.slice(1),regIdx,e.screenRows,screenIdx),/CN1_ONLY_COUNT_UNVERIFIABLE/);
});
check("CN1 count fails closed on discrepant N status",()=>{
  const e=prepare({cn1:1});
  e.screenRows[2][screenIdx.cN]="cN0";
  assert.throws(()=>ctx.countCn1OnlyRegistered_(e.regRows.slice(1),regIdx,e.screenRows,screenIdx),/CN1_ONLY_COUNT_UNVERIFIABLE/);
});
check("20 pre-existing CN1-only cases reject 21st without writes",()=>{
  const e=prepare({cn1:20});
  const r=finalize(e);
  assert.equal(r.ok,false);assert.equal(r.error,"CN1_CAP_REACHED");
  assert.equal(e.writes,0);assert.equal(e.sheets.Registry.rows.length,21);
});
check("19 pre-existing CN1-only cases allow 20th",()=>{
  const e=prepare({cn1:19});
  const r=finalize(e);
  assert.equal(r.ok,true);assert.equal(r.counts_after.cN1,20);
  assert.equal(r.counts_after.total,20);assert.equal(e.writes,3);
});
check("cT4N1M0 does not consume CN1-only cap",()=>{
  const e=prepare({cn1:20,target:{cT:"cT4"}});
  const r=finalize(e);
  assert.equal(r.ok,true);assert.equal(r.counts_after.cN1,20);
  assert.equal(r.counts_after.total,21);
});
check("cT3N1M1 does not consume CN1-only cap",()=>{
  const e=prepare({cn1:20,target:{cM:"cM1"}});
  const r=finalize(e);
  assert.equal(r.ok,true);assert.equal(r.counts_after.cN1,20);
});
check("42 existing registrations block 43rd without writes",()=>{
  const e=prepare({extra:42,target:{cN:"cN0"}});
  const r=finalize(e);
  assert.equal(r.ok,false);assert.equal(r.error,"TOTAL_CAP_REACHED");
  assert.equal(e.writes,0);
});
check("42-existing override permits manual total-cap exception",()=>{
  const e=prepare({extra:42,target:{cN:"cN0"},settings:{ALLOW_TOTAL_AFTER_MAX:"TRUE"}});
  const r=finalize(e);
  assert.equal(r.ok,true);assert.equal(r.counts_after.total,43);
});
check("12 existing SD registrations hold additional SD without writes",()=>{
  const e=prepare({sd:12,target:{cN:"cN0",best_effect:"SD"}});
  const r=finalize(e);
  assert.equal(r.ok,false);assert.equal(r.error,"SD_CAP_HOLD");assert.equal(e.writes,0);
});
check("11 existing SD registrations allow 12th SD",()=>{
  const e=prepare({sd:11,target:{cN:"cN0",best_effect:"SD"}});
  const r=finalize(e);
  assert.equal(r.ok,true);assert.equal(r.counts_after.SD,12);
});
check("SD threshold exception permits additional SD",()=>{
  const e=prepare({sd:12,target:{cN:"cN0",best_effect:"SD"},settings:{ALLOW_SD_AFTER_THRESHOLD:"TRUE"}});
  const r=finalize(e);
  assert.equal(r.ok,true);assert.equal(r.counts_after.SD,13);
});
check("cT3N2M0 does not increment CN1-only count",()=>{
  const e=prepare({cn1:20,target:{cT:"cT3",cN:"cN2",cM:"cM0"}});
  const r=finalize(e);
  assert.equal(r.ok,true);assert.equal(r.counts_after.cN1,20);
});
check("cTaN1M0 consumes CN1-only slot",()=>{
  const e=prepare({cn1:19,target:{cT:"cTa",cN:"cN1",cM:"cM0"}});
  const r=finalize(e);
  assert.equal(r.ok,true);assert.equal(r.counts_after.cN1,20);
});
check("VOID registration excluded from total cap",()=>{
  const e=prepare({extra:42,target:{cN:"cN0"}});
  e.regRows[1][regIdx.status]="VOID";
  const r=finalize(e);
  assert.equal(r.ok,true);assert.equal(r.counts_after.total,42);
});
check("VOID CN1-only registration frees one CN1 slot",()=>{
  const e=prepare({cn1:20});
  e.regRows[1][regIdx.status]="VOID";
  const r=finalize(e);
  assert.equal(r.ok,true);assert.equal(r.counts_after.cN1,20);
});
check("VOID SD registration excluded from SD hold count",()=>{
  const e=prepare({sd:12,target:{cN:"cN0",best_effect:"SD"}});
  e.regRows[1][regIdx.status]="VOID";
  const r=finalize(e);
  assert.equal(r.ok,true);assert.equal(r.counts_after.SD,12);
});
console.log("Completed "+passed+" offline quota checks against source GAS, with no external writes.");

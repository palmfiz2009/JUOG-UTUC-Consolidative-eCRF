/* Verify ScreeningCRF snapshot round matches central MDT active review round.
 * Uses real Apps Script code, mock data only. No Google Sheet writes.
 */
"use strict";
const assert=require("node:assert/strict"), fs=require("node:fs"),vm=require("node:vm"),path=require("node:path");
const code=fs.readFileSync(path.resolve(__dirname,"..","05_registry_google_apps_script.gs"),"utf8");
const ctx=vm.createContext({Logger:{log() {}}});
vm.runInContext(code,ctx,{timeout:5000});
let activeRound=1;
let found=true;
const columns=["screening_id","record_version","payload_json"];
let snapshots=[];
ctx.mockSpreadsheet={
  getSheetByName: sheetName=>{
    if(sheetName!=="ScreeningCRF" && sheetName!=="Screening_CRF") {
      // Accept the actual constant in the source below.
      if(sheetName!==vm.runInContext("SCREENING_CRF_SHEET",ctx)) throw Error("wrong sheet:"+sheetName);
    }
    return {getDataRange:()=>({getValues:()=>[columns,...snapshots]})};
  },
};
vm.runInContext("getSpreadsheet_ = function(){return mockSpreadsheet;};",ctx);
ctx.findScreening_ = () => found ? {
  row:[activeRound],idx:{review_round:0}
}:null;
function row(version,round,tag="") {
  return ["JUOG-SCR-999",version,JSON.stringify({screening_id:"JUOG-SCR-999",review_round:round,
    data:{synthetic_marker:tag||("round-"+round)}})];
}
function get(){return ctx.getScreeningCrf_({screening_id:"JUOG-SCR-999"});}
let passed=0;
function check(name,fn){fn();passed++;console.log("PASS "+name);}
check("current round 1 screening CRF is returned",()=>{
  activeRound=1;snapshots=[row(1,1)];
  const r=get();assert.equal(r.ok,true);assert.equal(r.payload.review_round,1);
  assert.equal(r.record_version,1);
});
check("resubmission to round 2 rejects stale round 1 snapshot",()=>{
  activeRound=2;snapshots=[row(1,1)];
  const r=get();assert.equal(r.ok,false);assert.equal(r.error,"SCREENING_CRF_ROUND_MISMATCH");
});
check("latest round 2 snapshot passes and older round 1 remains intact",()=>{
  activeRound=2;snapshots=[row(1,1),row(2,2)];
  const r=get();assert.equal(r.ok,true);assert.equal(r.record_version,2);
  assert.equal(r.payload.data.synthetic_marker,"round-2");
  assert.equal(snapshots.length,2);
});
check("round 3 cannot render a saved round 2 CRF",()=>{
  activeRound=3;snapshots=[row(1,1),row(2,2)];
  assert.equal(get().error,"SCREENING_CRF_ROUND_MISMATCH");
});
check("missing active screening fails closed even if old CRF is present",()=>{
  activeRound=1;found=false;snapshots=[row(1,1)];
  assert.equal(get().error,"SCREENING_NOT_FOUND");
  found=true;
});
check("missing current CRF fails closed",()=>{
  snapshots=[];
  assert.equal(get().error,"SCREENING_CRF_NOT_FOUND");
});
check("unparseable latest CRF fails closed",()=>{
  activeRound=1;snapshots=[["JUOG-SCR-999",1,"invalid JSON"]];
  assert.equal(get().error,"SCREENING_CRF_JSON_ERROR");
});
check("unrelated screening ID never surfaces another subject",()=>{
  activeRound=1;snapshots=[["JUOG-SCR-888",1,JSON.stringify({review_round:1})]];
  assert.equal(get().error,"SCREENING_CRF_NOT_FOUND");
});
console.log("Completed "+passed+"/8 central MDT round integrity checks.");
if(passed!==8)process.exitCode=1;

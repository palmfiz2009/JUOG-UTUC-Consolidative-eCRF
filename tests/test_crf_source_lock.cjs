/* CRF source version / registry checks must share the official append lock.
 * Real Apps Script function, mocked side effects, no external Sheets or credentials.
 */
"use strict";
const assert = require("node:assert/strict");
const fs=require("node:fs"), vm=require("node:vm"), path=require("node:path");
const code=fs.readFileSync(path.resolve(__dirname,"..","05_registry_google_apps_script.gs"),"utf8");
const c=vm.createContext({Logger:{log() {}}});
vm.runInContext(code,c,{timeout:5000});
const p={
  registration_id:"JUOG-999",facility_code:"F11",crf_type:"day90",visit:"90d",
  record_key:"JUOG-999|day90|90d",submission_id:"SYNTHETIC-SAVE",
  submission_kind:"初回報告",data:{visit_date:"2026-08-01"}
};
let count=0;
function check(name,fn){fn();count++;console.log("PASS "+name);}
function harness(options={}){
  let locked=false, released=0,attempts=0,trace=[];
  c.LockService={getScriptLock:()=>({
    tryLock:()=>{attempts++;trace.push("lock");
      if(options.busy)return false;
      locked=true;return true;},
    releaseLock:()=>{assert.equal(locked,true);locked=false;released++;trace.push("unlock");}
  })};
  c.validateSubject_ = () => {
    assert.equal(locked,true,"registry check must be under lock");
    trace.push("registry");
    return options.badRegistry?{ok:false,error:"SUBJECT_NOT_FOUND"}:{ok:true,registration_date:"2026-01-01"};
  };
  c.validateDay90SourceLink_ = () => {
    assert.equal(locked,true,"30d source verification must be under lock");
    trace.push("source");
    return options.stale?{ok:false,error:"SOURCE_CRF_UPDATED"}:{ok:true};
  };
  c.validateCrfHardStops_ = () => {
    assert.equal(locked,true,"date/consent checks must be under lock");
    trace.push("hard");
    return options.invalidDates?{ok:false,error:"HARD_VALIDATION_FAILED"}:{ok:true};
  };
  c.savePayloadToSheet_ = () => {
    assert.equal(locked,true,"append must be under the same lock");
    trace.push("append");
    if(options.appendThrows)throw new Error("SIMULATED_APPEND_ERROR");
    return {ok:true,record_version:1};
  };
  return {trace,lockInfo:()=>({locked,released,attempts})};
}
check("validation and append occur within one lock in a fixed sequence",()=>{
  const t=harness();
  const r=c.saveCrf_({payload:p});
  assert.equal(r.ok,true);
  assert.deepEqual(t.trace,["lock","registry","source","hard","append","unlock"]);
  assert.deepEqual(t.lockInfo(),{locked:false,released:1,attempts:1});
});
check("stale 30d CRF is detected before append and lock is released",()=>{
  const t=harness({stale:true});
  assert.equal(c.saveCrf_({payload:p}).error,"SOURCE_CRF_UPDATED");
  assert.deepEqual(t.trace,["lock","registry","source","unlock"]);
  assert.equal(t.lockInfo().released,1);
});
check("missing registry subject returns safely with lock released",()=>{
  const t=harness({badRegistry:true});
  assert.equal(c.saveCrf_({payload:p}).error,"SUBJECT_NOT_FOUND");
  assert.deepEqual(t.trace,["lock","registry","unlock"]);
});
check("invalid clinical chronology blocks append under lock",()=>{
  const t=harness({invalidDates:true});
  assert.equal(c.saveCrf_({payload:p}).error,"HARD_VALIDATION_FAILED");
  assert.deepEqual(t.trace,["lock","registry","source","hard","unlock"]);
});
check("lock contention prevents all reads and writes",()=>{
  const t=harness({busy:true});
  assert.equal(c.saveCrf_({payload:p}).error,"LOCK_TIMEOUT");
  assert.deepEqual(t.trace,["lock"]);
  assert.equal(t.lockInfo().released,0);
});
check("exception during append always releases the lock",()=>{
  const t=harness({appendThrows:true});
  assert.throws(()=>c.saveCrf_({payload:p}),/SIMULATED_APPEND_ERROR/);
  assert.deepEqual(t.trace,["lock","registry","source","hard","append","unlock"]);
  assert.equal(t.lockInfo().locked,false);
});
console.log("Completed "+count+"/6 source-lock unit tests.");
if(count!==6)process.exitCode=1;

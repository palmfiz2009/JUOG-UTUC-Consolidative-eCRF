// AUTH-04: real GAS privacy routines with entirely synthetic values.
// No network, real IDs, patient records or credentials.
import fs from "node:fs";
import assert from "node:assert/strict";

const code = fs.readFileSync("05_registry_google_apps_script.gs","utf8");
const beginning = code.indexOf("function directIdentifierKey_(key) {");
const ending = code.indexOf("function isCn1Only_(cT, cN, cM) {",beginning);
assert(beginning>=0 && ending>beginning,"real GAS privacy helpers must be available");
const src = code.slice(beginning,ending);
const impl = new Function(src+
  "\nreturn {directIdentifierKey_,containsDirectIdentifier_,stripDirectIdentifiers_};")();

const denied = [
  ["screening draft full DOB", {reg_birth_date:{type:"date",value:"1980-01-02"}}],
  ["widget full DOB", {widget_reg_birth_date:"1980-01-02"}],
  ["camel case date", {regBirthDate:"1980-01-02"}],
  ["patient name", {patientName:"SAMPLE ONLY"}],
  ["first name", {FirstName:"SAMPLE ONLY"}],
  ["last name", {lastName:"SAMPLE ONLY"}],
  ["MRN field", {patient_mrn:"12345"}],
  ["patient address", {patientAddress:"SAMPLE ADDRESS"}],
  ["patient phone", {patientPhone:"000-0000"}],
  ["DOB field", {date_of_birth:"1980-01-02"}],
  ["Japanese name key", {"患者氏名":"架空の患者"}],
  ["Japanese DOB key", {"患者生年月日":"1980-01-02"}],
  ["chart number key", {"カルテ番号":"FICTIONAL"}],
  ["free text explicit birth date", {notes:"生年月日1980年1月2日"}],
  ["free text MRN", {notes:"MRN: 12345"}],
  ["nested JSON string", {notes:JSON.stringify({data:{reg_birth_date:"1980-01-02"}})}],
  ["array nested object", {data:[{medical_record_number:"9999"}]}],
  ["free text patient name", {notes:"患者氏名:架空の人"}],
];
for(const [name,payload] of denied){
 assert.equal(impl.containsDirectIdentifier_(payload),true,name);
 console.log("PASS rejects",name);
}
const accepted=[
  ["age and birth month", {birth_year_month:"1980-01",age_at_consent:45}],
  ["other clinical dates", {consent_date:"2026-11-01",operation_date:"2026-11-10"}],
  ["unlabeled clinical date", {notes:"2026-11-01"]},
  ["clinical history without identifier", {notes:"既往歴：高血圧、糖尿病"}],
  ["explicit instruction not DOB", {notes:"生年月日を入力しないでください。"}],
  ["ordinary screening fields", {reg_ecog:{type:"value",value:"0"},reg_age:{type:"value",value:45}}],
];
for(const [name,payload] of accepted){
 assert.equal(impl.containsDirectIdentifier_(payload),false,name);
 console.log("PASS permits",name);
}
const legacy={
  reg_birth_date:{type:"date",value:"1980-01-02"},
  reg_age:{type:"value",value:45},
  reg_past_history:{type:"value",value:"生年月日:1980年1月2日"},
  deeply:{patientName:"SAMPLE",note:"高血圧"},
  array:[{lastName:"SAMPLE",vital:"normal"}],
  nested_json:JSON.stringify({birthDate:"1980-01-02",age:45}),
};
const redacted=impl.stripDirectIdentifiers_(legacy);
assert.equal("reg_birth_date" in redacted,false);
assert.equal(redacted.reg_age.value,45);
assert.equal(redacted.reg_past_history.value,"[REDACTED]");
assert.equal("patientName" in redacted.deeply,false);
assert.equal(redacted.deeply.note,"高血圧");
assert.equal("lastName" in redacted.array[0],false);
assert.equal(JSON.parse(redacted.nested_json).age,45);
assert.equal("birthDate" in JSON.parse(redacted.nested_json),false);
assert.equal(legacy.reg_birth_date.value,"1980-01-02","must not alter source row in memory");
assert.equal(code.split("draft_state:stripDirectIdentifiers_(draftState)").length-1,2,
  "both screening and post-registration draft reads must mask legacy identifiers");
assert.equal(code.split("if (containsDirectIdentifier_(draftState)) return {ok:false, error:'DIRECT_IDENTIFIER_NOT_ALLOWED'};").length-1,2,
  "both draft write APIs must enforce the guard");
console.log("PASS legacy read-time masking without rewriting original");
console.log("ALL AUTH-04 PRIVACY CONTRACTS PASSED");

// AUTH-04: real doPost exception boundary should never echo raw backend errors.
// Entirely local, fictional properties and error sentinel. No network or secrets.
import fs from "node:fs";
import assert from "node:assert/strict";
const code=fs.readFileSync("05_registry_google_apps_script.gs","utf8");
const start=code.indexOf("function doPost(e) {");
const stop=code.indexOf("/** Look up the uncoerced subject code",start);
assert(start>=0&&stop>start,"Actual GAS doPost source anchor");
const src=code.slice(start,stop);
const FAKE_SECRET="FICTIONAL_RAW_ERROR_CONTAINS_SENSITIVE_VALUE";
const mocks={
 PropertiesService:{getScriptProperties:()=>({getProperty:()=> "FICTIONAL_API_TOKEN"})},
 authorizeJuogAction_:()=>{throw Error(FAKE_SECRET);},
 jsonResponse_:x=>x,
};
const doPost=new Function(...Object.keys(mocks),src+"\nreturn doPost;")(...Object.values(mocks));
const result=doPost({postData:{contents:JSON.stringify({token:"FICTIONAL_API_TOKEN",action:"backend_info",payload:{}})}});
assert.equal(result.ok,false);
assert.equal(result.error,"SERVER_ERROR");
assert(!JSON.stringify(result).includes(FAKE_SECRET));
assert(!Object.hasOwn(result,"message"));
const wrongToken=doPost({postData:{contents:JSON.stringify({token:"INVALID",action:"backend_info"})}});
assert.equal(wrongToken.error,"UNAUTHORIZED");
assert(!JSON.stringify(wrongToken).includes(FAKE_SECRET));
for(const codePattern of [
  /error:'DRAFT_PARSE_ERROR',\s*message\s*:/,
  /error:'SOURCE_PAYLOAD_PARSE_ERROR',\s*message\s*:/,
  /error:\s*'SERVER_ERROR',\s*message\s*:/
])assert(!codePattern.test(code),"raw parser/server exception message must never surface");
console.log("PASS real doPost error suppression, unauthorized boundary and parser response contracts");

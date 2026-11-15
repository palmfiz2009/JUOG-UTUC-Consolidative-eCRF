// Demonstrates the *known* shared-token facility-access gap in the original
// deployed-style GAS, for release risk accounting. It is NOT a security PASS.
// No tokens, credentials, network, patient information, or live sheet access.
import fs from "node:fs";
import assert from "node:assert/strict";

const src=fs.readFileSync("05_registry_google_apps_script.gs","utf8");
const start=src.indexOf("function authorizeJuogAction_(action, actor, payload, props) {");
const end=src.indexOf("function reviewerMdtProgressOnly_(result) {",start);
assert(start>=0 && end>start,"real GAS authorization function was not located");
const fun=new Function("REVIEWER_ROLES",src.slice(start,end)+
  "\nreturn authorizeJuogAction_;")(["radiology","medical_oncology","urology"]);
const props={getProperty:name=>({
  JUOG_ADMIN_ACTION_TOKEN:"NOT_A_REAL_SECRET",
  JUOG_REVIEWER_RADIOLOGY_ACTION_TOKEN:"NOT_A_REAL_SECRET"
})[name]||""};
const weakFacilityActions=[
  "submit_screening","save_crf","save_screening_draft","save_draft",
  "get_draft","get_screening_draft","delete_draft","get_crf_linkage","validate",
];
const testActor=null;
for(const action of weakFacilityActions){
  const r=fun(action,testActor,{},props);
  assert.equal(r.ok,true,action+" must be reviewed before closing the known identity gap");
  assert.equal(r.kind,"facility");
}
for(const action of ["finalize_mdt","list_screenings","submit_mdt_review","get_mdt_reviews"]){
  const r=fun(action,null,{},props);
  assert.equal(r.ok,false);
  assert.equal(r.error,"ROLE_AUTH_REQUIRED");
}
console.log("KNOWN GCP P0 GAP CONFIRMED: "+weakFacilityActions.length+
  " facility endpoints accept a shared-server-token context without an individual verified principal.");
console.log("This is a RELEASE BLOCKER, not a PASS: personal OIDC+facility ACL and audit attribution remain unverified.");

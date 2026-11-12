// Scoped regression of the newly separated AUTH_CONNECT branch; no live traffic.
const fs0=require('fs'),vm0=require('vm');
const harness=fs0.readFileSync(__dirname+'/test_session_b2.cjs','utf8').split('const call=e=>')[0];
const tests=`
c.sessionExecutionStage='AUTH_CONNECT';c.authConnectReviewApproved=true;c.authConnectReviewRef='LOCAL-SCOPED-REVIEW';
c.allRoutesReviewed=false;c.schemaParityApproved=false;delete c.resumeDerivationKey;delete c.draftPepper;
const originalJournal=JSON.stringify(journal),checks=[];
const request=(action='ui_context',payload={id:'context',action:'ui_context',payload:{registration_id:''}},changes={})=>env(action,payload,changes);
const call=e=>x.juogUnifiedIsolationEntryV3_(e,c);
function test(name,f){f();assert.equal(JSON.stringify(journal),originalJournal);checks.push(name);}
test('scoped context works without business approvals or business keys',()=>{const r=call(request());assert.equal(r.ok,true);assert.equal(r.role,'facility');assert.equal(r.facility_code,'TEST01');assert.equal(r.business_writes_allowed,false);});
test('no business sheet is opened by context',()=>{const orig=ss.getSheetByName;ss.getSheetByName=n=>{assert.ok(['V3_Users','V3_SessionEvents'].includes(n));return orig(n);};try{assert.equal(call(request()).ok,true);}finally{ss.getSheetByName=orig;}});
test('missing scoped review denied without session events',()=>{const n=events.length;c.authConnectReviewApproved=false;assert.equal(call(request()).error,'AUTH_CONNECT_NOT_APPROVED');assert.equal(events.length,n);c.authConnectReviewApproved=true;});
test('invalid signature denied',()=>{const e=request();e.identity_assertion=e.identity_assertion.slice(0,-6)+'AAAAAA';assert.equal(call(e).error,'AUTH_INVALID');});
test('replay denied in a fresh GAS context',()=>{const e=request();assert.equal(call(e).ok,true);x=context();assert.equal(call(e).error,'ASSERTION_REPLAY');});
test('all business and recovery actions rejected',()=>{for(const action of ['save_crf','submit_screening','prepare_request','execute_request','list_requests','request_status','save_draft','read_crf']){const payload=['prepare_request','execute_request','list_requests','request_status'].includes(action)?{}:{id:'denied',action,payload:{}};assert.equal(call(request(action,payload)).error,'AUTH04_EXECUTION_NOT_APPROVED');}});
test('case-specific context rejected',()=>assert.equal(call(request('ui_context',{id:'context',action:'ui_context',payload:{registration_id:'JUOG-001'}})).error,'AUTH_CONNECT_CONTEXT_ONLY'));
test('other facility and admin role denied',()=>{acl[1][5]='["OTHER"]';assert.equal(call(request()).error,'ACL_DENIED');acl[1][5]='["TEST01"]';acl[1][4]='admin';assert.equal(call(request()).error,'ACL_DENIED');acl[1][4]='facility';});
test('revoked and expired ACL denied',()=>{acl[1][3]=false;assert.equal(call(request()).error,'ACL_DENIED');acl[1][3]=true;const expiry=acl[1][6];acl[1][6]='2000-01-01T00:00:00Z';assert.equal(call(request()).error,'ACL_DENIED');acl[1][6]=expiry;});
test('logout invalidates an already issued signature',()=>{const pending=request();assert.equal(call(request('session_revoke',{})).revoked,true);x=context();assert.equal(call(pending).error,'SESSION_REVOKED');});
sid=hash('second-session');
test('expired signature denied',()=>{const e=request();now+=15;assert.equal(call(e).error,'AUTH_EXPIRED');});
test('session expiration denied',()=>{now=origin+3600;assert.equal(call(request()).error,'SESSION_INVALID');now=origin+30;});
test('concurrent lock is fail closed',()=>{locked=true;assert.equal(call(request()).error,'LOCK_TIMEOUT');locked=false;});
test('scope cannot enter AUTH04 with business approval flags false',()=>{c.sessionExecutionStage='AUTH04_APPROVED';assert.equal(call(request()).error,'INTEGRATION_NOT_APPROVED');c.sessionExecutionStage='AUTH_CONNECT';});
test('unknown stage denied',()=>{c.sessionExecutionStage='UNKNOWN';assert.equal(call(request()).error,'ISOLATION_NOT_APPROVED');c.sessionExecutionStage='AUTH_CONNECT';});
const result={count:checks.length,checks,result:'PASS',journal_unchanged:true,scope:'Offline synthetic isolated GAS AUTH_CONNECT only',formal_uat_delta:0};
fs.writeFileSync(root+'/../uat_evidence/auth_connect_scope_regression_20261113.json',JSON.stringify(result,null,2)+'\\n');console.log(JSON.stringify(result));
`;
vm0.runInThisContext('(function(require,__dirname){'+harness+tests+'})',{filename:__filename})(require,__dirname);

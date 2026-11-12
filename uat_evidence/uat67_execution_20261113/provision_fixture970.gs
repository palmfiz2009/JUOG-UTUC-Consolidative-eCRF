/* Editor-only, one fixed fictional setup transaction. No doPost route.
 * No principal spoofing/ACL grant. The setup actor is explicitly administrative,
 * not a claim of clinical or OIDC submission. Run only after independent review.
 */
function juogProvisionFixture970Core_(d){
 const id='AUTH04_FIXTURE_20261113_JUOG970',action='ISOLATED_FIXTURE_INITIALIZATION';
 const actor={id:'PI_AUTHORIZED_FIXTURE_SETUP',enabled:true,role:'fixture_setup'};
 const expected={registered_at:'2026-04-01',registration_id:'JUOG-970',status:'ACTIVE',facility_code:'TEST01',facility_name:'完全架空施設',consent_date:'2026-03-25'};
 d.guard();const before=d.store.read(),baselineHash=d.hash(JSON.stringify(before.baseline));
 if(!before.baseline||!Array.isArray(before.baseline.Registry))throw Error('FIXTURE_BASELINE_SCHEMA');
 for(const [name,rows] of Object.entries(before.baseline)){if(!Array.isArray(rows)||rows.length!==1||!Array.isArray(rows[0]))throw Error('FIXTURE_BASELINE_NOT_EMPTY');}
 if((before.requests||[]).length||(before.requestEvents||[]).length)throw Error('FIXTURE_REQUESTS_EXIST');
 for(const key of ['intents','audits','commits'])if((before[key]||[]).some(r=>r.id!==id))throw Error('FIXTURE_OTHER_TRANSACTIONS_EXIST');
 const payload={fixture_id:'JUOG-970',facility_code:'TEST01',approval_ref:'PI_INTEGRATED_EXECUTION_20261113',fixture_manifest_sha256:d.fixtureSha};
 const svc=new JuogDomainServiceV3({authenticate:()=>actor,authorize:(u,a,p)=>({ok:u.id===actor.id&&a===action&&JSON.stringify(p)===JSON.stringify(payload),error:'FIXTURE_SCOPE_INVALID'}),privacy:()=>false,hash:d.hash,now:d.now,withLock:f=>f(),store:d.store,
  plan:(a,p,t)=>{d.guard();const after=JSON.parse(JSON.stringify(t));const h=after.Registry[0];if(new Set(h).size!==h.length||Object.keys(expected).some(k=>!h.includes(k)))throw Error('FIXTURE_REGISTRY_SCHEMA');if(after.Registry.length!==1)throw Error('FIXTURE_ALREADY_POPULATED');after.Registry.push(h.map(k=>expected[k]||''));return {ok:true,after,result:{fixture_id:'JUOG-970',fictional:true},audit_detail:{scope:'EDITOR_ONLY_FICTIONAL_INITIALIZATION',approval_ref:payload.approval_ref,fixture_manifest_sha256:d.fixtureSha,synthetic_business_dates:true,actual_initialization_at:d.now(),no_clinical_submission_claim:true}};}});
 const result=svc.execute('editor-fixed-setup',{id,action,payload,expected_revision:0});if(!result.ok)return result;
 const after=d.store.read(),view=svc.readView(),h=view.tables.Registry[0];
 if(d.hash(JSON.stringify(after.baseline))!==baselineHash||view.revision!==1||view.tables.Registry.length!==2)throw Error('FIXTURE_READBACK_MISMATCH');
 if(JSON.stringify(view.tables.Registry[1])!==JSON.stringify(h.map(k=>expected[k]||'')))throw Error('FIXTURE_ROW_MISMATCH');
 for(const [name,rows] of Object.entries(before.baseline)){if(name!=='Registry'&&JSON.stringify(view.tables[name])!==JSON.stringify(rows))throw Error('FIXTURE_UNRELATED_CHANGE');}
 if(Object.keys(view.tables).some(k=>!(k in before.baseline)))throw Error('FIXTURE_UNEXPECTED_TABLE');
 if(['intents','audits','commits'].some(k=>after[k].length!==1||after[k][0].id!==id))throw Error('FIXTURE_AUDIT_COUNT');
 return {ok:true,existing:result.existing,revision:1,fixture_id:'JUOG-970',registry_count:1,baseline_unchanged:true,other_tables_unchanged:true,setup_actor_not_oidc:true};
}
function juogRunAuth04Fixture970(){
 const script='11wSp4ePaP5b5A2b5ITZZSZa3YTe-Ex-Tu6oGlEkkRfkPrMCA4deVSZDy',sheet='1Hd6EHDPZe8zGcDbILkaBLubgF5atfAzRfpPSN5LemiU';
 const props=PropertiesService.getScriptProperties(),lock=LockService.getScriptLock();let diagnosticStage='LOCK';
 function report(r){const safe=['FIXTURE_LOCK_TIMEOUT','FIXTURE_ISOLATION_REQUIRED','FIXTURE_ACL_CHANGED','FIXTURE_PRINCIPAL_CHANGED','DOMAIN_STORE_SCHEMA','BASELINE_MISSING','JOURNAL_HASH_MISMATCH','JOURNAL_CONFLICT','JOURNAL_INCOMPLETE','DOMAIN_INCOMPLETE','FIXTURE_PROVISIONING_INCOMPLETE'];const o={ok:r.ok===true,stage:diagnosticStage,error:r.error?(safe.includes(r.error)?r.error:'FIXTURE_PROVISIONING_INCOMPLETE'):null};if(r.ok===true){o.revision=r.revision;o.existing=r.existing===true;o.fixture_id='JUOG-970';}console.info(JSON.stringify(o));return r;}
 function guard(){if(ScriptApp.getScriptId()!==script||!lock.hasLock())throw Error('FIXTURE_ISOLATION_REQUIRED');const c=JSON.parse(props.getProperty('UNIFIED_ISOLATION_CONFIG')||'null');if(!c||c.environment!=='ISOLATED_TEST'||c.spreadsheetId!==sheet||c.approvedSpreadsheetId!==sheet||c.sessionExecutionStage!=='AUTH_CONNECT'||c.sessionPolicy!=='isolated_gas_session_b2'||c.sessionStoreGeneration!=='d72bcf33-423d-4c4d-862d-2e2d69bc3edf'||c.authConnectReviewApproved!==true||typeof c.authConnectReviewRef!=='string'||!c.authConnectReviewRef.trim()||c.fictionalBaselineVerified!==true||typeof c.approvalRef!=='string'||!c.approvalRef.trim()||c.notificationsDisabled!==true||c.backupVerified!==true||c.qaApproved!==true)throw Error('FIXTURE_ISOLATION_REQUIRED');}
 if(!lock.tryLock(30000))return report({ok:false,error:'FIXTURE_LOCK_TIMEOUT'});
 try{diagnosticStage='CONFIG';guard();diagnosticStage='ACL';const ss=SpreadsheetApp.openById(sheet);const acl=ss.getSheetByName('V3_Users').getDataRange().getValues();const expectedHeader=['issuer','subject','user_id','enabled','role','facility_ids_json','valid_until'];if(acl.length!==2||JSON.stringify(acl[0])!==JSON.stringify(expectedHeader)||acl[1][2]!=='UAT_TEST01_PI_01'||acl[1][3]!==true||acl[1][4]!=='facility'||acl[1][5]!=='["TEST01"]'||acl[1][6]!=='2026-11-19T23:59:00+09:00')throw Error('FIXTURE_ACL_CHANGED');
  const hash=s=>Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256,s,Utilities.Charset.UTF_8).map(b=>('0'+((b+256)%256).toString(16)).slice(-2)).join('');
  diagnosticStage='PRINCIPAL';if(hash(JSON.stringify(['JUOG-ACL-PROPOSAL-v1',String(acl[1][0]),String(acl[1][1])]))!=='f0ea0ddb132e96bbd08cba4e37dc38609b73db5740530a05225c5acb6cab798f')throw Error('FIXTURE_PRINCIPAL_CHANGED');
  diagnosticStage='DOMAIN_STORE_AND_TRANSACTION';return report(juogProvisionFixture970Core_({guard,hash,now:()=>new Date().toISOString(),fixtureSha:'0747f9ac3f59a6e230cc6cc6debaebde3138578ec82741567e995ab1e2d0d126',store:juogDomainSheetsStoreV3_(ss,hash,()=>Utilities.getUuid(),guard)}));
 }catch(e){const safe=['FIXTURE_ISOLATION_REQUIRED','FIXTURE_ACL_CHANGED','FIXTURE_PRINCIPAL_CHANGED','DOMAIN_STORE_SCHEMA','BASELINE_MISSING','JOURNAL_HASH_MISMATCH','JOURNAL_CONFLICT','JOURNAL_INCOMPLETE'];return report({ok:false,error:safe.includes(e.message)?e.message:'FIXTURE_PROVISIONING_INCOMPLETE'});}finally{lock.releaseLock();}
}

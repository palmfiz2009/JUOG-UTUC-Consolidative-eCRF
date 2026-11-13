/* Independent candidate contract checks; offline only. Supply candidate .gs. */
const fs=require('fs'),assert=require('assert/strict'),crypto=require('crypto');
const file=process.argv[2];if(!file)throw Error('CANDIDATE_FILE_REQUIRED');
const source=fs.readFileSync(file,'utf8');
const f=new Function(source+';return {operation:juogAuth04Operation_,request:juogAuth04Request_};')();
let passed=0;const rows=[];
function check(name,fn,allow){let permitted=true;try{fn()}catch(e){permitted=false;}assert.equal(permitted,allow,name);rows.push({name,allowed:permitted});passed++;}
function payload(id='JUOG-971',facility='TEST01',type='perioperative_30d',visit='30d'){return {registration_id:id,facility_code:facility,crf_type:type,visit,record_key:[id,type,visit].join('|'),reporter_email:'fictional@example.invalid'};}
for(const [type,visit] of [['perioperative_30d','30d'],['day90','90d'],['followup','6m']]){
 check('971 '+type+' save',()=>f.operation({action:'save_crf',payload:payload('JUOG-971','TEST01',type,visit)}),true);
}
for(const id of ['JUOG-970','JUOG-972','JUOG-001',''])check(id+' save denied',()=>f.operation({action:'save_crf',payload:payload(id)}),false);
check('foreign facility denied',()=>f.operation({action:'save_crf',payload:payload('JUOG-971','TEST02')}),false);
check('wrong visit denied',()=>f.operation({action:'save_crf',payload:payload('JUOG-971','TEST01','followup','9m')}),false);
check('mismatched key denied',()=>f.operation({action:'save_crf',payload:{...payload(),record_key:'JUOG-970|perioperative_30d|30d'}}),false);
check('real-looking reporter denied',()=>f.operation({action:'save_crf',payload:{...payload(),reporter_email:'someone@example.com'}}),false);
for(const action of ['void_registration','finalize_mdt','submit_screening','delete_draft','reset_draft_code'])check(action+' denied',()=>f.operation({action,payload:payload()}),false);
check('prepare971',()=>f.request({action:'prepare_request',payload:{action:'save_crf',payload:payload()}}),true);
check('prepare970 denied',()=>f.request({action:'prepare_request',payload:{action:'save_crf',payload:payload('JUOG-970')}}),false);
check('context971',()=>f.request({action:'ui_context',payload:{action:'ui_context',payload:{registration_id:'JUOG-971'}}}),true);
check('context970 denied',()=>f.request({action:'ui_context',payload:{action:'ui_context',payload:{registration_id:'JUOG-970'}}}),false);
check('direct save denied',()=>f.request({action:'save_crf',payload:payload()}),false);
check('execute extra fields denied',()=>f.request({action:'execute_request',payload:{operation_id:'fixture',role:'admin'}}),false);
check('status empty id denied',()=>f.request({action:'request_status',payload:{operation_id:''}}),false);
console.log(JSON.stringify({scope:'OFFLINE_INDEPENDENT_SCOPE_TEST_ONLY',source_sha256:crypto.createHash('sha256').update(source).digest('hex'),passed,results:rows,formal_uat_delta:0},null,2));

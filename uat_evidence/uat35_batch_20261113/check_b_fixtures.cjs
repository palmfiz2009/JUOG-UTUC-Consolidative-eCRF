// Offline, pinned deployed-v5 validator. No Sheets or network access.
const fs=require('fs'),crypto=require('crypto'),assert=require('assert/strict'),path=require('path');
const source=fs.readFileSync('/workspace/shared/juog_auth04_editor_v5.gs','utf8');
const sha=crypto.createHash('sha256').update(source).digest('hex');
assert.equal(sha,'99b602bb7cbfd8672f0478c1eb0a21daa68891ae746428e2ae7d082b4d7504a5');
const validate=new Function(source+';return validateClinicalV3;')();
const old=path.resolve(__dirname,'../uat67_execution_20261113');
const surgery=JSON.parse(fs.readFileSync(old+'/surgical_fixture_candidate.json')).payload;
const nonop=JSON.parse(fs.readFileSync(old+'/fixture_candidate.json')).crfs;
const reg={status:'ACTIVE',facility_code:'TEST01',registration_date:'2026-04-01',consent_date:'2026-03-25'};
const results=[],fixtures=[];
function check(id,ids,base,mutate,ok,code,store={records:[],events:[]}){
 let p=structuredClone(base);mutate(p);const r=validate(p,reg,'2026-11-13',store);
 assert.equal(r.ok,ok,id+':'+JSON.stringify(r));if(code)assert(r.errors.includes(code),id+':'+JSON.stringify(r));
 results.push({scenario:id,uat_ids:ids,ok:r.ok,errors:r.errors,warnings:r.warnings});fixtures.push({scenario:id,payload:p,expected_ok:ok,expected_internal_error:code||null});
}
check('B01_surgical_zero',['POST-01','POST-03','POST-04'],surgery,p=>{p.data.pathology.size_mm=0},true);
for(const [id,date,ok] of [['B02_day30','2026-05-13',true],['B03_day31_in_30d','2026-05-14',false]])
 check(id,['POST-01','POST-02'],surgery,p=>Object.assign(p.data,{cd_grade_30:'Grade IIIa',cd_event_date_30:date,cd_detail_30:'完全架空イベント',cd_surgery_relation:'関連する'}),ok,ok?null:'COMPLICATION_WINDOW');
check('B04_path_reason_missing',['POST-04'],surgery,p=>p.data.pathology.ypt='評価不能',false,'REQUIRED:eval_failed_reason');
check('B05_path_reason_restored',['POST-04'],surgery,p=>Object.assign(p.data.pathology,{ypt:'評価不能',eval_failed_reason:'完全架空の評価不能理由'}),true);
check('B06_other_histology_missing',['POST-04'],surgery,p=>p.data.pathology.histology='その他',false,'REQUIRED:histology_other');
check('B07_other_histology_restored',['POST-04'],surgery,p=>Object.assign(p.data.pathology,{histology:'その他',histology_other:'完全架空の病理詳細'}),true);
const sourceRecord={transaction_id:'OFFLINE-SOURCE',record_version:1,submission_id:nonop[0].submission_id,payload:nonop[0]};
const store={records:[sourceRecord],events:[{transaction_id:'OFFLINE-SOURCE',kind:'COMMITTED'}]};
check('B08_stale_reference',['POST-06'],nonop[1],p=>p.data.source_30d_record_version=0,false,'SOURCE_STALE_OR_MISMATCH',store);
check('B09_correct_reference',['POST-06'],nonop[1],()=>{},true,null,store);
check('B10_death_missing_cause',['FUP-01','FUP-02'],nonop[2],p=>Object.assign(p.data,{vital_status:'死亡',death_date:'2026-10-13'}),false,'REQUIRED:death_cause',store);
check('B11_death_complete',['FUP-01','FUP-02'],nonop[2],p=>Object.assign(p.data,{vital_status:'死亡',death_date:'2026-10-13',death_cause:'他病死'}),true,null,store);
check('B12_recurrence_missing_details',['FUP-01','FUP-02'],nonop[2],p=>p.data.intraluminal_recurrence_status='今回新規あり',false,'REQUIRED:intraluminal_recurrence_date',store);
check('B13_pd_after_visit',['FUP-02'],nonop[2],p=>Object.assign(p.data,{recist_progression_status:'今回PDあり',progression_date:'2026-10-14',progression_sites:['肺'],progression_detail:'完全架空'}),false,'ORDER:progression_date:visit_date',store);
check('B14_recurrence_complete',['FUP-01'],nonop[2],p=>Object.assign(p.data,{intraluminal_recurrence_status:'今回新規あり',intraluminal_recurrence_date:'2026-10-01',intraluminal_sites:['膀胱'],intraluminal_treatment:['経過観察']}),true,null,store);
const out={scope:'OFFLINE_VALIDATOR_ONLY_NO_LIVE_PASS',source_sha256:sha,passed:results.length,results,fixtures,formal_pass_delta:0,limitation:'Accepted clinical payload is not proof of API authorization, saving, restore, audit or aggregation. Operation envelopes/versions must be bound at live preparation.'};
fs.writeFileSync(__dirname+'/b_fixture_results.json',JSON.stringify(out,null,2)+'\n');console.log(results.length+' offline branch checks passed');

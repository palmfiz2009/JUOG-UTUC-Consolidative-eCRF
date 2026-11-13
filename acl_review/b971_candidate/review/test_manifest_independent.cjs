const fs=require('fs'),crypto=require('crypto'),assert=require('assert/strict'),path=require('path');
const src=fs.readFileSync(process.argv[2],'utf8'),root=path.dirname(process.argv[2]);
const validate=new Function(src+';return validateClinicalV3;')();
const manifest=JSON.parse(fs.readFileSync(root+'/uat_auth04_fixture.json'));
const reg={status:'ACTIVE',facility_code:'TEST01',registration_date:'2026-04-01',consent_date:'2026-03-25'};
const store={records:[],events:[]},results=[];
for(const [idx,step] of manifest.steps.entries()){
 const p=step.payload,expectedOk=!step.expected_error;
 const actual=validate(p,reg,'2026-11-13',store);
 assert.equal(actual.ok,expectedOk,step.name+':'+JSON.stringify(actual));
 const versions=store.records.filter(r=>r.record_key===p.record_key).map(r=>r.record_version),latest=versions.length?Math.max(...versions):0;
 assert.equal(p.expected_record_version,latest,step.name+' base version');
 if(expectedOk){const id='offline-'+idx;store.records.push({transaction_id:id,record_key:p.record_key,record_version:latest+1,submission_id:p.submission_id,payload:structuredClone(p)});store.events.push({transaction_id:id,kind:'COMMITTED'});}
 results.push({name:step.name,uat_ids:step.uat_ids,ok:actual.ok,internal_errors:actual.errors,warnings:actual.warnings,before_version:latest,after_version:expectedOk?latest+1:latest});
}
console.log(JSON.stringify({scope:'OFFLINE_MANIFEST_VALIDATOR_AND_VERSION_SEQUENCE_ONLY',passed:results.length,source_sha256:crypto.createHash('sha256').update(src).digest('hex'),fixture_sha256:crypto.createHash('sha256').update(fs.readFileSync(root+'/uat_auth04_fixture.json')).digest('hex'),results,formal_uat_delta:0},null,2));

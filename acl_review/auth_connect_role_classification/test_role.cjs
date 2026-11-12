const fs=require('fs'),vm=require('vm'),assert=require('assert');
const p=__dirname+'/auth_bridge.gs',c={};vm.createContext(c);vm.runInContext(fs.readFileSync(p,'utf8'),c);
const headers=['issuer','subject','user_id','enabled','role','facility_ids_json','valid_until'];
function run(role,facility='["TEST01"]',enabled=true,expiry='2099-01-01T00:00:00Z') {const rows=[headers,['fixture-issuer','fixture-subject','fixture-user',enabled,role,facility,expiry]];return c.juogV3ReadIndividualAcl_({getSheetByName:()=>({getDataRange:()=>({getValues:()=>rows})})},'fixture-issuer','fixture-subject');}
assert.throws(()=>run('invalid_role'),/ACL_DENIED/);
assert.equal(run('facility').enabled,true);
assert.equal(run('facility','["TEST01"]',false).enabled,false);
assert.equal(run('facility','["TEST01"]',true,'2000-01-01T00:00:00Z').enabled,false);
assert.throws(()=>run('facility','{}'),/ACL_INVALID/);
console.log('5 offline role/ACL regression checks PASS; no live requests');

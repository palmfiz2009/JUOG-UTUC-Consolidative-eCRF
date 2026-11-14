// Reuse the existing full signed recovery fixture with the NEW runtime guard.
// Entirely in-memory; no network or actual credentials.
const fs=require('fs'),path=require('path'),vm=require('vm');
const oldDir=path.resolve(__dirname,'../server_recovery_candidate');
const manifest=JSON.parse(fs.readFileSync(path.join(__dirname,'manifest.json')));
for(const [input,output] of [['test_readonly_activation.cjs','readonly_results.json'],['test_full_signed_entry.cjs','full_entry_results.json']]){
let test=fs.readFileSync(path.join(oldDir,input),'utf8');
test=test.replace("__dirname+'/bundle_recovery_candidate.gs'",JSON.stringify(path.join(__dirname,'recovery_candidate.gs')));
test=test.replace('ea70e3970a10a405cebdcf6f049ce2f426a91337dadc8846b5a9886b0a382383',manifest.find(x=>x.base==='recovery').candidate_sha256);
const original='getProperty:k=>props.get(k)';
if(!test.includes(original))throw Error('FIXTURE_CHANGED');
test=test.replace(original,`getProperty:k=>{
 if(k==='UNIFIED_ISOLATION_CONFIG'){
  const cfg={...c};delete cfg.signingKey;delete cfg.resumeDerivationKey;delete cfg.draftPepper;return JSON.stringify(cfg);
 }
 if(k==='ADMIN_BRIDGE_SIGNING_KEY')return c.signingKey;
 if(k==='ADMIN_RESUME_DERIVATION_KEY')return c.resumeDerivationKey;
 if(k==='ADMIN_DRAFT_PEPPER')return c.draftPepper;
 return props.get(k);
}`);
test=test.replace("__dirname+'/"+output+"'",JSON.stringify(path.join(__dirname,output)));
vm.runInNewContext(test,{require,console,Buffer,structuredClone,__dirname:oldDir},{filename:'runtime_snapshot_guard_full_signed_recovery.cjs'});
}

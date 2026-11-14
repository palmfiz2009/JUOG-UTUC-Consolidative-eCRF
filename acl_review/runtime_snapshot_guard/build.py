"""Build undeployed isolated candidates; preserve both original source bundles."""
from pathlib import Path
import hashlib,json,difflib
P=Path(__file__).parent
helper='''
// Recheck inside the same ScriptLock used for session and business operations.
// Never log configuration or credentials. A change requires a fresh request.
function juogRequireCurrentRuntimeSnapshot_(snapshot) {
 try {
  const props=PropertiesService.getScriptProperties();
  const raw=props.getProperty('UNIFIED_ISOLATION_CONFIG');
  if(!raw)throw Error('CONFIGURATION_CHANGED');
  const current=JSON.parse(raw);
  current.signingKey=props.getProperty('ADMIN_BRIDGE_SIGNING_KEY');
  current.resumeDerivationKey=props.getProperty('ADMIN_RESUME_DERIVATION_KEY');
  current.draftPepper=props.getProperty('ADMIN_DRAFT_PEPPER');
  function stable(v){
   if(Array.isArray(v))return '['+v.map(stable).join(',')+']';
   if(v&&typeof v==='object')return '{'+Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+stable(v[k])).join(',')+'}';
   return JSON.stringify(v);
  }
  if(stable(current)!==stable(snapshot))throw Error('CONFIGURATION_CHANGED');
 }catch(_){throw Error('CONFIGURATION_CHANGED');}
}
'''
files=[('version9',P.parent/'b971_candidate/bundle_prepare_view_candidate.gs','6d75109c4fffda3ebe4aedb0d7990f1d694ef3a331dcdb2123c10399279970d6'),('recovery',P.parent/'server_recovery_candidate/bundle_recovery_candidate.gs','ea70e3970a10a405cebdcf6f049ce2f426a91337dadc8846b5a9886b0a382383')]
manifest=[]
for label,path,pin in files:
 source=path.read_text();assert hashlib.sha256(source.encode()).hexdigest()==pin
 old=' try {\n  const auth=juogV3DecodeBridge_(envelope,c),req=auth.request;'
 assert source.count(old)==1
 changed=source.replace(old,' try {\n  juogRequireCurrentRuntimeSnapshot_(c);\n  const auth=juogV3DecodeBridge_(envelope,c),req=auth.request;',1)
 catch="}catch(e){const safe=['AUTH04_SCOPE_DENIED','AUTH_REQUIRED'"
 assert changed.count(catch)==1
 changed=changed.replace(catch,"}catch(e){const safe=['CONFIGURATION_CHANGED','AUTH04_SCOPE_DENIED','AUTH_REQUIRED'",1)+helper
 (P/f'{label}_candidate.gs').write_text(changed)
 (P/f'{label}.patch').write_text(''.join(difflib.unified_diff(source.splitlines(True),changed.splitlines(True),fromfile=path.name,tofile=f'{label}_candidate.gs')))
 manifest.append({'base':label,'base_sha256':pin,'candidate_sha256':hashlib.sha256(changed.encode()).hexdigest(),'deployed':False})
(P/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')

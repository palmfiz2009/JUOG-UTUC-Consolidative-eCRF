"""Build an undeployed local overlay only; never access settings or deploy it."""
import hashlib,json
from pathlib import Path
P=Path(__file__).resolve().parent
FILES={'streamlit_app.py':'readonly_streamlit_entry.py','readonly_probe.py':'readonly_probe.py','content_fingerprint.py':'content_fingerprint.py'}
REQUIRED=('canonical_v9_bridge.py','uat_b2_auth_bridge.py','uat_auth_connect.py','auth_diagnostics.py')
def build(base,destination):
 base=Path(base).resolve();destination=Path(destination).resolve()
 if destination.exists():raise ValueError('DESTINATION_MUST_NOT_EXIST')
 if destination==base or base in destination.parents:raise ValueError('OUTPUT_MUST_BE_OUTSIDE_APP')
 # Inspect named code dependencies only. Never copy an app directory or secrets.
 dependencies={name:hashlib.sha256((base/name).read_bytes()).hexdigest() for name in REQUIRED}
 contents={target:(P/source).read_bytes() for target,source in FILES.items()}
 for name,data in contents.items():compile(data,name,'exec')
 destination.mkdir(parents=True)
 for name,data in contents.items():(destination/name).write_bytes(data)
 manifest={'kind':'UNDEPLOYED_READONLY_OVERLAY','deployed':False,'activation_authorized':False,'files':{name:hashlib.sha256(data).hexdigest() for name,data in contents.items()},'required_existing_code_sha256':dependencies,'limitations':['Import validation is not runtime/OIDC/ACL or live recovery validation.','Existing form and dependencies remain in the target app; this is not a standalone app.','Separate review and approval required before any reflection or setting change.']}
 (destination/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 return manifest
if __name__=='__main__':
 import argparse
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--base-code',required=True);parser.add_argument('--output',required=True)
 args=parser.parse_args();build(args.base_code,args.output)
 print('UNDEPLOYED_OVERLAY_BUILT_NO_SETTINGS_CHANGED')

"""Offline suite entry; refuses all Python TCP connections, logs each suite separately.
Run from repository root using Python with requirements.txt installed.
No deployment, CI dispatch, app hosting, Sheets access or SMTP is performed.
"""
import json,os,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).parent.resolve();out=ROOT/'integration_evidence';out.mkdir(exist_ok=True)
bootstrap="""import socket,unittest,sys
def denied(*a,**k):raise AssertionError('OFFLINE_NETWORK_DENIED')
socket.socket.connect=denied
socket.create_connection=denied
suite=unittest.defaultTestLoader.discover(sys.argv[1],pattern=sys.argv[2])
r=unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(not r.wasSuccessful())
"""
jobs=[('fixture',ROOT/'fixture_regression',[sys.executable,'-c',bootstrap,'.','test_*.py']),
      ('fixture_bridge_entry',ROOT/'fixture_regression',[sys.executable,'-c',bootstrap,'.','offline_test_*.py']),
      ('pr',ROOT,[sys.executable,'-c',bootstrap,'tests','test_*.py']),
      ('adapter',ROOT,[sys.executable,'-c',bootstrap,'integration_tests','test_*.py']),
      ('endpoint',ROOT,['node','integration_tests/test_endpoint.cjs']),
      ('pr_gas',ROOT,['node','tests/test_crf_audit_repair.mjs']),
      ('pr_identity',ROOT,['node','tests/test_screening_identity.mjs'])]
results=[]
for name,cwd,cmd in jobs:
 with (out/(name+'.log')).open('w') as log:
  r=subprocess.run(cmd,cwd=cwd,stdout=log,stderr=subprocess.STDOUT,env={**os.environ,'PYTHONPATH':str(cwd)},timeout=90)
 results.append({'suite':name,'exit_code':r.returncode});print(name,r.returncode,flush=True)
(out/'summary.json').write_text(json.dumps({'mode':'OFFLINE_ONLY','suites':results,'formal_uat_pass_delta':0,'independent_qa_approved':False},indent=2)+'\n')
sys.exit(any(r['exit_code'] for r in results))

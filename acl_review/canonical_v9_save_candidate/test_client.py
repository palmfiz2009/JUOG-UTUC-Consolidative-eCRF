import sys,json,tempfile,subprocess,copy,unittest
from pathlib import Path
P=Path(__file__).parent;sys.path[:0]=[str(P),str(P.parent/'canonical_v9_integration')]
from client import Client,BridgeError
from juog_common import redact_draft_identifiers
BASE=json.loads((P.parent/'canonical_v9_integration/canonical_fixture.json').read_text())['payload']
class T(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.rpc=subprocess.Popen(['node',str(P/'domain_rpc.cjs')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True);self.calls=[];self.drop=None
  self.identity={'issuer':'https://offline.invalid','subject':'OFFLINE','environment':'JUOG_AUTH04_ISOLATED_TEST01'};self.c=Client(self.call,redact_draft_identifiers,self.tmp.name+'/state.db',lambda:self.identity)
 def tearDown(self):self.c.close();self.rpc.terminate();self.rpc.wait();self.tmp.cleanup()
 def call(self,a,p):
  self.calls.append((a,copy.deepcopy(p)));self.rpc.stdin.write(json.dumps({'action':a,'payload':p})+'\n');self.rpc.stdin.flush();r=json.loads(self.rpc.stdout.readline())
  if self.drop==a:self.drop=None;raise TimeoutError('OFFLINE_LOST_RESPONSE')
  return r
 def test_initial_correction_read_audit(self):
  self.assertEqual(self.c.read()['record_version'],0);r=self.c.write(BASE);self.assertEqual(r['record_version'],1)
  with self.assertRaises(BridgeError):self.c.write(BASE)
  one=self.call('inspect',{})['records'][0]
  self.assertEqual(self.c.read()['record_version'],1)
  q=dict(BASE,submission_kind='訂正報告',correction_reason='架空訂正');q=copy.deepcopy(q);q['data']['pathology']['size_mm']=0
  r=self.c.write(q);self.assertEqual(r['record_version'],2)
  state=self.call('inspect',{});self.assertEqual(state['audits'],2);self.assertEqual(state['records'][0],one)
 def test_execution_response_loss_restart_reconcile(self):
  self.c.read();self.drop='execute_request'
  with self.assertRaises(TimeoutError):self.c.write(BASE)
  pending=self.c.pending();self.assertEqual(len(pending),1);opid=[p['operation_id'] for a,p in self.calls if a=='execute_request'][0]
  self.c.close();self.c=Client(self.call,redact_draft_identifiers,self.tmp.name+'/state.db',lambda:self.identity)
  r=self.c.reconcile(pending[0]);self.assertEqual(r['operation_id'],opid);self.assertEqual(r['state'],'SAVED')
  self.assertEqual(sum(a=='prepare_request' for a,p in self.calls),1);self.assertEqual(self.call('inspect',{})['audits'],1)
 def test_prepare_response_loss_blocks_reprepare(self):
  self.c.read();self.drop='prepare_request'
  with self.assertRaises(TimeoutError):self.c.write(BASE)
  with self.assertRaises(BridgeError):self.c.write(BASE)
  self.assertEqual(sum(a=='prepare_request' for a,p in self.calls),1);self.assertEqual(self.call('inspect',{})['audits'],0)
 def test_wrong_owner_cannot_reconcile(self):
  self.c.read();self.drop='execute_request'
  with self.assertRaises(TimeoutError):self.c.write(BASE)
  pending=self.c.pending()[0];other=Client(self.call,redact_draft_identifiers,self.tmp.name+'/state.db',lambda:dict(self.identity,subject='OTHER'))
  with self.assertRaises(BridgeError):other.reconcile(pending)
  other.close()
 def test_malformed_read_does_not_seed_version(self):
  self.c.transport=lambda a,p:{'ok':True,'read_only':True,'result':{'ok':True,'records':[{'record_version':99}]}}
  with self.assertRaises(BridgeError):self.c.read()
  with self.assertRaises(BridgeError):self.c.write(BASE)
 def test_identifier_rejected_before_prepare(self):
  self.c.read();q=copy.deepcopy(BASE);q['data']['patient_name']='FICTIONAL'
  with self.assertRaises(BridgeError):self.c.write(q)
  self.assertEqual(sum(a=='prepare_request' for a,p in self.calls),0)
 def test_readback_content_mismatch_blocks_success(self):
  self.c.read();original=self.c.transport
  def corrupt(a,p):
   r=original(a,p)
   if a=='read_crf' and r.get('result',{}).get('records'):r['result']['records'][0]['payload']['data']['pathology']['size_mm']=987654
   return r
  self.c.transport=corrupt
  with self.assertRaisesRegex(BridgeError,'SAVE_CONTENT_MISMATCH'):self.c.write(BASE)
  self.assertEqual(len(self.c.pending()),1)
 def test_principal_change_after_read(self):
  self.c.read();self.identity['subject']='OTHER'
  with self.assertRaisesRegex(BridgeError,'PRINCIPAL_CHANGED'):self.c.write(BASE)
  self.assertEqual(sum(a=='prepare_request' for a,p in self.calls),0);self.assertEqual(self.c.pending(),[])
 def test_stale_observed_version_rejected(self):
  self.c.read();self.c.write(BASE);self.c.read()
  q=copy.deepcopy(BASE);q.update(submission_kind='訂正報告',correction_reason='架空訂正',expected_record_version=1,submission_id='OFFLINE-CONCURRENT',schema_version='review-v3-unapproved')
  prep=self.call('prepare_request',{'action':'save_crf','payload':q});self.call('execute_request',{'operation_id':prep['operation_id']})
  q['data']['pathology']['size_mm']=0
  r=self.c.write(q);self.assertEqual(r['state'],'FAILED');self.assertEqual(self.call('inspect',{})['audits'],2)
 def test_two_instances_same_attempt_no_duplicate(self):
  other=Client(self.call,redact_draft_identifiers,self.tmp.name+'/state.db',lambda:self.identity)
  self.c.read();other.read();a=self.c.write(BASE);b=other.write(BASE)
  self.assertEqual(a['operation_id'],b['operation_id']);self.assertEqual(self.call('inspect',{})['audits'],1);other.close()
 def test_store_failure_prevents_prepare(self):
  self.c.read();self.c.close()
  with self.assertRaises(Exception):self.c.write(BASE)
  self.assertEqual(sum(a=='prepare_request' for a,p in self.calls),0)
if __name__=='__main__':
 r=unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(T));(P/'results.json').write_text(json.dumps({'tests':r.testsRun,'passed':r.wasSuccessful(),'mode':'OFFLINE_PYTHON_CLIENT_ACTUAL_V9_DOMAIN_LOCAL_SQLITE','live_storage_approved':False,'network_calls':0,'formal_pass_delta':0},indent=2)+'\n');sys.exit(not r.wasSuccessful())

import sys,json,subprocess,unittest,copy
from pathlib import Path
P=Path(__file__).parent;sys.path[:0]=[str(P),str(P.parent/'canonical_v9_integration')]
from recovery_client import discover,KEY
BASE=json.loads((P.parent/'canonical_v9_integration/canonical_fixture.json').read_text())['payload']
class T(unittest.TestCase):
 def setUp(self):
  self.rpc=subprocess.Popen(['node',str(P/'domain_recovery_rpc.cjs')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True);self.calls=[]
 def tearDown(self):self.rpc.terminate();self.rpc.wait();self.rpc.stdin.close();self.rpc.stdout.close()
 def call(self,a,p):
  self.calls.append(a);self.rpc.stdin.write(json.dumps({'action':a,'payload':p})+'\n');self.rpc.stdin.flush();return json.loads(self.rpc.stdout.readline())
 def prepare(self):
  p=copy.deepcopy(BASE);p.update(expected_record_version=0,submission_id='OFFLINE-RECOVER',schema_version='review-v3-unapproved');return self.call('prepare_request',{'action':'save_crf','payload':p})
 def test_lost_prepare_response_discovered_without_write(self):
  original=self.prepare();self.assertTrue(original['ok']);before=self.call('inspect',{})
  r=discover(self.call);self.assertEqual(r['operation_id'],original['operation_id']);self.assertFalse(r['may_execute']);self.assertEqual(self.call('inspect',{}),before)
  self.assertEqual(self.calls.count('prepare_request'),1);self.assertNotIn('execute_request',self.calls)
 def test_committed_request_found_without_duplicate(self):
  p=self.prepare();saved=self.call('execute_request',{'operation_id':p['operation_id']});before=self.call('inspect',{});self.assertEqual(before['audits'],1)
  r=discover(self.call);self.assertEqual(r['state'],'NO_PENDING_OBSERVED');self.assertFalse(r['may_prepare']);self.assertEqual(r['requests'][0]['operation_id'],p['operation_id']);self.assertEqual(r['requests'][0]['state'],'SAVED');self.assertEqual(self.call('inspect',{}),before)
if __name__=='__main__':
 r=unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(T));(P/'domain_recovery_results.json').write_text(json.dumps({'tests':r.testsRun,'passed':r.wasSuccessful(),'mode':'OFFLINE_ACTUAL_V9_DOMAIN_LIFECYCLE_WITH_CANDIDATE_RECOVERY_MEMORY_STORE','live_network_calls':0,'formal_pass_delta':0},indent=2)+'\n');sys.exit(not r.wasSuccessful())

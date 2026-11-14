"""Run the real GAS lifecycle in memory; bypass client preflight deliberately."""
import copy,json,subprocess,unittest
from pathlib import Path
P=Path(__file__).parent.resolve()
BASE=json.loads((P.parent/'canonical_v9_integration/canonical_fixture.json').read_text())['payload']
class ServerReasonTests(unittest.TestCase):
 def setUp(self):
  runner=(P/'domain_recovery_rpc.cjs').read_text().replace('const source=','let source=',1)
  self.rpc=subprocess.Popen(['node','-e',runner],cwd=P,stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
  p=self.payload('initial',0);p['submission_kind']='初回報告'
  r=self.save(p);self.assertTrue(r['ok'],r)
 def tearDown(self):
  self.rpc.terminate();self.rpc.wait();self.rpc.stdin.close();self.rpc.stdout.close()
 def call(self,a,p):
  self.rpc.stdin.write(json.dumps({'action':a,'payload':p})+'\n');self.rpc.stdin.flush();return json.loads(self.rpc.stdout.readline())
 def payload(self,sid,version):
  p=copy.deepcopy(BASE);p.update(expected_record_version=version,submission_id='OFFLINE-'+sid,schema_version='review-v3-unapproved',submission_kind='訂正報告');return p
 def save(self,p):
  r=self.call('prepare_request',{'action':'save_crf','payload':p})
  return self.call('execute_request',{'operation_id':r['operation_id']}) if r.get('ok') else r
 def test_invalid_reason_does_not_write_crf_or_business_audit(self):
  before=self.call('inspect',{})
  for i,value in enumerate([None,0,False,True,123,[],{},'', '  ','\u3000\n']):
   with self.subTest(index=i):
    p=self.payload('invalid-'+str(i),1);p['correction_reason']=value
    r=self.save(p);self.assertFalse(r.get('ok'),r)
    after=self.call('inspect',{})
    for key in ['revision','audits','records']:self.assertEqual(after[key],before[key],key)
 def test_valid_correction_preserves_original_and_reason(self):
  before=self.call('inspect',{})
  p=self.payload('valid',1);p['correction_reason']=' 架空データの訂正 '
  r=self.save(p);self.assertTrue(r.get('ok'),r)
  after=self.call('inspect',{});self.assertEqual(after['audits'],before['audits']+1)
  self.assertEqual(len(after['records']),2)
  self.assertEqual(after['records'][0],before['records'][0])
  self.assertEqual(after['records'][-1]['payload']['correction_reason'],p['correction_reason'])
if __name__=='__main__':unittest.main()

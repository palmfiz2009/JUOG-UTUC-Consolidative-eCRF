import sys,json,tempfile,subprocess,copy,unittest
from pathlib import Path
P=Path(__file__).parent;sys.path[:0]=[str(P),str(P.parent/'canonical_v9_save_candidate'),str(P.parent/'canonical_v9_integration')]
from recoverable_client import RecoverableClient,BridgeError
from juog_common import redact_draft_identifiers
BASE=json.loads((P.parent/'canonical_v9_integration/canonical_fixture.json').read_text())['payload']
class T(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.rpc=subprocess.Popen(['node',str(P/'domain_recovery_rpc.cjs')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True);self.calls=[];self.drop=True;self.corrupt=False
  self.c=RecoverableClient(self.call,redact_draft_identifiers,self.tmp.name+'/state.db',lambda:{'issuer':'https://offline.invalid','subject':'OFFLINE','environment':'JUOG_AUTH04_ISOLATED_TEST01'})
 def tearDown(self):self.c.close();self.rpc.terminate();self.rpc.wait();self.rpc.stdin.close();self.rpc.stdout.close();self.tmp.cleanup()
 def call(self,a,p):
  self.calls.append(a);self.rpc.stdin.write(json.dumps({'action':a,'payload':p})+'\n');self.rpc.stdin.flush();r=json.loads(self.rpc.stdout.readline())
  if a=='prepare_request' and self.drop:self.drop=False;raise TimeoutError('OFFLINE_RESPONSE_LOSS')
  if a=='list_requests' and self.corrupt:r['requests'][0]['content_sha256']='0'*64
  return r
 def lost(self):
  self.c.read()
  with self.assertRaises(TimeoutError):self.c.write(BASE)
  return self.c.pending()[0]
 def test_recover_then_explicit_same_id_resume(self):
  d=self.lost();r=self.c.recover_prepare(d,BASE);self.assertEqual(r['state'],'UNFINISHED');oid=r['operation_id'];self.assertNotIn('execute_request',self.calls)
  r=self.c.resume(d);self.assertEqual(r['state'],'SAVED');self.assertEqual(r['operation_id'],oid);self.assertEqual(self.calls.count('prepare_request'),1);self.assertEqual(self.call('inspect',{})['audits'],1)
 def test_changed_content_denied_before_discovery(self):
  d=self.lost();q=copy.deepcopy(BASE);q['data']['pathology']['size_mm']=987
  with self.assertRaisesRegex(BridgeError,'CONTENT_MISMATCH'):self.c.recover_prepare(d,q)
  self.assertNotIn('list_requests',self.calls);self.assertNotIn('execute_request',self.calls)
 def test_server_content_mismatch_remains_unbound(self):
  d=self.lost();self.corrupt=True
  with self.assertRaisesRegex(BridgeError,'CONTENT_MISMATCH'):self.c.recover_prepare(d,BASE)
  self.assertIsNone(self.c._row(d)[3]);self.assertNotIn('execute_request',self.calls)
if __name__=='__main__':unittest.main()

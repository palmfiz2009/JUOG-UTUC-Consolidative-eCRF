import sys,json,unittest
from pathlib import Path
P=Path(__file__).parent;sys.path[:0]=[str(P),str(P.parent/'canonical_v9_integration')]
from signed_channel import SignedChannel
from canonical_v9_bridge import BridgeError
from test_bridge import native
class T(unittest.TestCase):
 def test_default_denies_before_transport(self):
  sent=[];c=SignedChannel(lambda:native,lambda e:sent.append(e))
  with self.assertRaises(BridgeError):c('read_crf',{})
  self.assertEqual(sent,[])
 def test_reuses_personal_signed_envelope(self):
  sent=[];c=SignedChannel(lambda:native,lambda e:sent.append(e) or {'ok':True},guard=lambda:None)
  c('request_status',{'operation_id':'OFFLINE'});self.assertEqual(json.loads(sent[0]['request_json'])['action'],'request_status');self.assertIn('identity_assertion',sent[0]);self.assertNotIn('token',sent[0]);self.assertEqual(c.identity()['environment'],'JUOG_AUTH04_ISOLATED_TEST01')
 def test_allowlist(self):
  c=SignedChannel(lambda:native,lambda e:self.fail(),guard=lambda:None)
  with self.assertRaises(BridgeError):c('export_csv',{})
if __name__=='__main__':unittest.main()

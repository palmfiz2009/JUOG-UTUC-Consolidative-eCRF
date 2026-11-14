import sys,json,unittest
from pathlib import Path
P=Path(__file__).parent;sys.path[:0]=[str(P),str(P.parent/'canonical_v9_save_candidate'),str(P.parent/'canonical_v9_integration')]
from recovery_channel import RecoveryChannel,BridgeError
from test_bridge import native
Q={'registration_id':'JUOG-971','facility_code':'TEST01','record_key':'JUOG-971|perioperative_30d|30d'}
class T(unittest.TestCase):
 def test_second_guard_defaults_deny(self):
  c=RecoveryChannel(lambda:native,lambda e:self.fail(),guard=lambda:None)
  with self.assertRaises(BridgeError):c('list_requests',Q)
 def test_scope_and_signed_read(self):
  sent=[];c=RecoveryChannel(lambda:native,lambda e:sent.append(e),guard=lambda:None,recovery_guard=lambda:None)
  with self.assertRaises(BridgeError):c('list_requests',dict(Q,facility_code='OTHER'))
  self.assertFalse(sent);c('list_requests',Q);self.assertEqual(json.loads(sent[0]['request_json']),{'action':'list_requests','payload':Q});self.assertIn('identity_assertion',sent[0]);self.assertNotIn('token',sent[0])
if __name__=='__main__':unittest.main()

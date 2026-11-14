import sys,unittest
from pathlib import Path
P=Path(__file__).parent;sys.path[:0]=[str(P),str(P.parent/'canonical_v9_save_candidate'),str(P.parent/'canonical_v9_integration')]
import test_recoverable_client as support
from recoverable_client import RecoverableClient,BridgeError
from juog_common import redact_draft_identifiers
class T(unittest.TestCase):
 setUp=support.T.setUp
 tearDown=support.T.tearDown
 call=support.T.call
 lost=support.T.lost
 def test_late_recovery_cannot_rewind_execution(self):
  d=self.lost();original=self.c.transport;injected=False
  def concurrent(a,p):
   nonlocal injected
   r=original(a,p)
   if a=='request_status' and not injected:
    injected=True;self.c._set(d,'EXECUTING',p['operation_id'])
   return r
  self.c.transport=concurrent;self.c.recover_prepare(d,support.BASE)
  self.assertEqual(self.c._row(d)[2],'EXECUTING')
  with self.assertRaisesRegex(BridgeError,'STATUS_ONLY'):self.c.resume(d)
  self.assertNotIn('execute_request',self.calls)
 def test_lost_local_store_cannot_prepare_again(self):
  self.lost();new=RecoverableClient(self.call,redact_draft_identifiers,self.tmp.name+'/new.db',self.c.identity)
  try:
   new.read()
   with self.assertRaisesRegex(BridgeError,'LOCAL_STATE_LOST'):new.write(support.BASE)
   self.assertEqual(self.calls.count('prepare_request'),1);self.assertEqual(self.call('inspect',{})['audits'],0)
  finally:new.close()
if __name__=='__main__':unittest.main()

import sys,unittest,copy,json
from pathlib import Path
P=Path(__file__).parent;sys.path[:0]=[str(P),str(P.parent/'canonical_v9_save_candidate'),str(P.parent/'canonical_v9_integration')]
import test_recoverable_client as support
BASE=support.BASE
from recoverable_client import BridgeError
class T(unittest.TestCase):
 setUp=support.T.setUp
 tearDown=support.T.tearDown
 call=support.T.call
 lost=support.T.lost
 def test_uncertain_execute_not_sent_twice(self):
  d=self.lost();self.c.recover_prepare(d,BASE);original=self.c.transport
  def timeout(a,p):
   if a=='execute_request':self.calls.append(a);raise TimeoutError('OFFLINE_BEFORE_DELIVERY')
   return original(a,p)
  self.c.transport=timeout
  with self.assertRaises(TimeoutError):self.c.resume(d)
  with self.assertRaisesRegex(BridgeError,'STATUS_ONLY'):self.c.resume(d)
  self.assertEqual(self.calls.count('execute_request'),1);self.assertEqual(self.call('inspect',{})['audits'],0)
 def test_unknown_phase_no_execute(self):
  d=self.lost();self.c.recover_prepare(d,BASE);original=self.c.transport
  def bad(a,p):
   r=original(a,p)
   if a=='request_status':r['phase']='UNKNOWN'
   return r
  self.c.transport=bad
  with self.assertRaisesRegex(BridgeError,'STATUS_PHASE_UNSAFE'):self.c.resume(d)
  self.assertNotIn('execute_request',self.calls)
if __name__=='__main__':unittest.main()

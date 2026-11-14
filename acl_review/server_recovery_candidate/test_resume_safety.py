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
 def test_audit_pending_never_executes_even_with_local_prepared(self):
  d=self.lost();self.c.recover_prepare(d,BASE);original=self.c.transport
  def pending(a,p):
   r=original(a,p)
   if a=='request_status':r.update(state='UNFINISHED',phase='AUDIT_OR_COMMIT_PENDING')
   return r
  self.c.transport=pending
  for _ in range(2):
   with self.assertRaisesRegex(BridgeError,'EXECUTION_UNCERTAIN_STATUS_ONLY'):self.c.resume(d)
  self.assertNotIn('execute_request',self.calls)
  self.assertEqual(self.c._row(d)[2],'PREPARED')
  self.assertEqual(self.call('inspect',{})['audits'],0)
 def test_recovered_audit_pending_remains_status_only(self):
  d=self.lost();original=self.c.transport
  def pending(a,p):
   r=original(a,p)
   if a=='request_status':r.update(state='UNFINISHED',phase='AUDIT_OR_COMMIT_PENDING')
   return r
  self.c.transport=pending
  result=self.c.recover_prepare(d,BASE)
  self.assertEqual(result['phase'],'AUDIT_OR_COMMIT_PENDING')
  with self.assertRaisesRegex(BridgeError,'EXECUTION_UNCERTAIN_STATUS_ONLY'):self.c.resume(d)
  self.assertNotIn('execute_request',self.calls)
if __name__=='__main__':unittest.main()

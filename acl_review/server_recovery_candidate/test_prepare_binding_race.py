"""Offline delayed prepare response interleaved with a second local client."""
import sys, unittest
from pathlib import Path
P=Path(__file__).parent
sys.path[:0]=[str(P),str(P.parent/'canonical_v9_save_candidate'),str(P.parent/'canonical_v9_integration')]
import test_recoverable_client as support
from recoverable_client import RecoverableClient, BridgeError
from juog_common import redact_draft_identifiers
class T(unittest.TestCase):
 setUp=support.T.setUp
 tearDown=support.T.tearDown
 call=support.T.call
 def test_late_prepare_response_cannot_rewind_uncertain_execute(self):
  self.drop=False;self.c.read();original=self.c.transport
  other=RecoverableClient(self.call,redact_draft_identifiers,self.tmp.name+'/state.db',self.c.identity)
  try:
   def interleaved(a,p):
    r=original(a,p)
    if a=='prepare_request':
     d=other.pending()[0]
     other.recover_prepare(d,support.BASE)
     def lost_execute(action,payload):
      if action=='execute_request':
       self.calls.append(action);raise TimeoutError('OFFLINE_EXECUTE_DELIVERY_UNKNOWN')
      return original(action,payload)
     other.transport=lost_execute
     with self.assertRaises(TimeoutError):other.resume(d)
     self.assertEqual(other._row(d)[2],'EXECUTING')
    return r
   self.c.transport=interleaved
   with self.assertRaisesRegex(BridgeError,'EXECUTION_UNCERTAIN_STATUS_ONLY'):self.c.write(support.BASE)
   d=self.c.pending()[0]
   self.assertEqual(self.c._row(d)[2],'EXECUTING')
   self.assertEqual(self.calls.count('prepare_request'),1)
   self.assertEqual(self.calls.count('execute_request'),1)
   self.assertEqual(self.call('inspect',{})['audits'],0)
  finally:other.close()
 def test_late_prepare_response_cannot_replace_conflicting_operation(self):
  self.drop=False;self.c.read();original=self.c.transport
  def conflict(a,p):
   r=original(a,p)
   if a=='prepare_request':
    d=self.c.pending()[0];self.c._set(d,'EXECUTING','OFFLINE-CONFLICT')
   return r
  self.c.transport=conflict
  with self.assertRaisesRegex(BridgeError,'PREPARE_BIND_CONFLICT'):self.c.write(support.BASE)
  self.assertEqual(self.c._row(self.c.pending()[0])[3],'OFFLINE-CONFLICT')
  self.assertNotIn('execute_request',self.calls)
if __name__=='__main__':unittest.main()

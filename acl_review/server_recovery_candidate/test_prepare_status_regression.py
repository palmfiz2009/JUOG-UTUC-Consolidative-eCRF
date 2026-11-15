"""Lost-prepare discovery must not rewind an already observed server outcome."""
import unittest
import test_recoverable_client as support
from recoverable_client import BridgeError

class PrepareStatusRegressionTests(unittest.TestCase):
 setUp=support.T.setUp
 tearDown=support.T.tearDown
 call=support.T.call
 lost=support.T.lost
 def check_regression(self,state,phase):
  digest=self.lost();original=self.c.transport;before=self.call('inspect',{})
  def inconsistent(action,payload):
   response=original(action,payload)
   if action=='list_requests':response['requests'][0].update(state=state,phase=phase)
   return response
  self.c.transport=inconsistent
  with self.assertRaisesRegex(BridgeError,'^RECOVERY_STATUS_REGRESSION$'):
   self.c.recover_prepare(digest,support.BASE)
  self.assertEqual(self.c._row(digest)[2],'PREPARING')
  self.assertIsNone(self.c._row(digest)[3])
  self.assertNotIn('execute_request',self.calls)
  self.assertEqual(self.call('inspect',{}),before)
 def test_committed_cannot_return_prepared(self):self.check_regression('SAVED','COMMITTED')
 def test_rejected_cannot_return_prepared(self):self.check_regression('FAILED','REJECTED_BEFORE_INTENT')
 def test_started_execution_cannot_return_prepared(self):self.check_regression('UNFINISHED','AUDIT_OR_COMMIT_PENDING')
 def test_completion_between_list_and_status_is_allowed(self):
  digest=self.lost();original=self.c.transport;advanced=False
  def advance(action,payload):
   nonlocal advanced
   if action=='request_status' and not advanced:
    advanced=True
    # Simulate an existing authorized worker completing the same offline request.
    self.call('execute_request',payload)
   return original(action,payload)
  self.c.transport=advance
  result=self.c.recover_prepare(digest,support.BASE)
  self.assertEqual(result['state'],'SAVED')
  self.assertEqual(self.c._row(digest)[2],'SAVED')
  self.assertEqual(self.calls.count('prepare_request'),1)
  self.assertEqual(self.calls.count('execute_request'),1)
  self.assertEqual(self.call('inspect',{})['audits'],1)

if __name__=='__main__':unittest.main()

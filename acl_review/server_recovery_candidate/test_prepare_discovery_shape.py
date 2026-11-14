"""Lost-prepare recovery must not bind from an invalid discovery response."""
import copy,unittest
import test_recoverable_client as support
from recoverable_client import BridgeError
class PrepareDiscoveryTests(unittest.TestCase):
 setUp=support.T.setUp
 tearDown=support.T.tearDown
 call=support.T.call
 lost=support.T.lost
 def check_invalid(self,mutate):
  digest=self.lost();original=self.c.transport;before=self.call('inspect',{})
  def corrupt(action,payload):
   response=original(action,payload)
   if action=='list_requests':mutate(response)
   return response
  self.c.transport=corrupt
  status_count=self.calls.count('request_status')
  with self.assertRaisesRegex(BridgeError,'^RECOVERY_ROW_INVALID$'):
   self.c.recover_prepare(digest,support.BASE)
  self.assertEqual(self.c._row(digest)[2],'PREPARING')
  self.assertIsNone(self.c._row(digest)[3])
  self.assertEqual(self.calls.count('request_status'),status_count)
  self.assertNotIn('execute_request',self.calls)
  self.assertEqual(self.call('inspect',{}),before)
 def test_unknown_state(self):
  self.check_invalid(lambda r:r['requests'][0].update(state='UNKNOWN'))
 def test_unexpected_payload_field(self):
  self.check_invalid(lambda r:r['requests'][0].update(payload={'patient_name':'OFFLINE_FAKE_MARKER'}))
 def test_duplicate_operation_different_submission(self):
  def mutate(r):
   duplicate=copy.deepcopy(r['requests'][0]);duplicate['submission_id']='OTHER-OFFLINE-SUBMISSION';r['requests'].append(duplicate)
  self.check_invalid(mutate)
if __name__=='__main__':unittest.main()

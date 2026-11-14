"""Offline corruption of persisted submission metadata must not confirm SAVED."""
import copy
import unittest
import test_client as support
from client import BridgeError

class ReadbackSubmissionTests(unittest.TestCase):
 setUp = support.T.setUp
 call = support.T.call
 def tearDown(self):
  self.c.close()
  self.rpc.terminate()
  self.rpc.wait()
  self.rpc.stdin.close()
  self.rpc.stdout.close()
  self.tmp.cleanup()
 def test_missing_payload_submission(self): check(self, 'missing')
 def test_different_payload_submission(self): check(self, 'different')
 def test_different_transaction(self): check(self, 'transaction')

def check(self, mode):
 self.c.read()
 original = self.c.transport
 def corrupt(action, payload):
  result = original(action, payload)
  if action == 'read_crf' and result.get('result', {}).get('records'):
   record = result['result']['records'][0]
   if mode == 'missing':
    record['payload'].pop('submission_id', None)
   elif mode == 'different':
    record['payload']['submission_id'] = 'OFFLINE-DIFFERENT-SUBMISSION'
   else:
    record['transaction_id'] = 'OFFLINE-DIFFERENT-TRANSACTION'
  return result
 self.c.transport = corrupt
 with self.assertRaisesRegex(BridgeError, 'SAVE_SUBMISSION_MISMATCH'):
  self.c.write(copy.deepcopy(support.BASE))
 self.assertEqual(len(self.c.pending()), 1)
 self.assertEqual(sum(a == 'execute_request' for a, p in self.calls), 1)
 # Corrupt only the response: real local fixture remains one record/audit.
 self.assertEqual(self.call('inspect', {})['audits'], 1)
 # Status-only reconciliation after restoring response succeeds, never re-executes.
 self.c.transport = original
 self.assertEqual(self.c.reconcile(self.c.pending()[0])['state'], 'SAVED')
 self.assertEqual(sum(a == 'execute_request' for a, p in self.calls), 1)

if __name__ == '__main__': unittest.main()

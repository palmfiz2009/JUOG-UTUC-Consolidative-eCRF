"""Offline readback must compare original content, not its masked projection."""
import copy
import unittest
import test_client as support
from client import BridgeError

class RawReadbackTests(unittest.TestCase):
 setUp = support.T.setUp
 call = support.T.call
 def tearDown(self):
  self.c.close(); self.rpc.terminate(); self.rpc.wait()
  self.rpc.stdin.close(); self.rpc.stdout.close(); self.tmp.cleanup()
 def check_injection(self, key, nested):
  self.c.read()
  original = self.c.transport
  marker = 'OFFLINE-IDENTIFIER-MARKER'
  def corrupt(action, payload):
   response = original(action, payload)
   if action == 'read_crf' and response.get('result', {}).get('records'):
    data = response['result']['records'][0]['payload']['data']
    (data['pathology'] if nested else data)[key] = marker
   return response
  self.c.transport = corrupt
  with self.assertRaisesRegex(BridgeError, '^SAVE_CONTENT_MISMATCH$') as raised:
   self.c.write(copy.deepcopy(support.BASE))
  self.assertNotIn(marker, str(raised.exception))
  self.assertEqual(len(self.c.pending()), 1)
  # Public reads must remain redacted even while confirmation is blocked.
  self.assertNotIn(marker, str(self.c.read()))
  self.c.transport = original
  self.assertEqual(self.c.reconcile(self.c.pending()[0])['state'], 'SAVED')
  self.assertEqual(sum(a == 'execute_request' for a,p in self.calls), 1)
  self.assertEqual(self.call('inspect', {})['audits'], 1)
 def test_added_patient_name_not_hidden_by_redaction(self): self.check_injection('patient_name', False)
 def test_nested_fullwidth_mrn_not_hidden_by_redaction(self): self.check_injection('ＭＲＮ', True)

if __name__ == '__main__': unittest.main()

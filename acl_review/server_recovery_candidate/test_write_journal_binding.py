"""Offline saved submission IDs must not conceal a different server request."""
import copy,unittest
import test_recoverable_client as support
from recoverable_client import BridgeError
class JournalBindingTests(unittest.TestCase):
 setUp=support.T.setUp
 tearDown=support.T.tearDown
 call=support.T.call
 def mismatch(self,field,value):
  self.drop=False;self.c.read();self.c.write(copy.deepcopy(support.BASE));self.c.read()
  before=self.call('inspect',{});original=self.c.transport
  def corrupt(a,p):
   r=original(a,p)
   if a=='list_requests':r['requests'][0][field]=value
   return r
  self.c.transport=corrupt
  p=copy.deepcopy(support.BASE);p.update(submission_kind='訂正報告',correction_reason='架空訂正')
  calls_before=self.calls.count('prepare_request')
  with self.assertRaises(BridgeError):self.c.write(p)
  self.assertEqual(self.calls.count('prepare_request'),calls_before)
  self.assertEqual(self.call('inspect',{}),before)
 def test_operation_mismatch(self):self.mismatch('operation_id','OTHER-OFFLINE-OPERATION')
 def test_version_mismatch(self):self.mismatch('expected_record_version',99)
 def test_unknown_state(self):self.mismatch('state','UNKNOWN')
 def test_consistent_journal_allows_valid_correction(self):
  self.drop=False;self.c.read();self.c.write(copy.deepcopy(support.BASE));self.c.read()
  p=copy.deepcopy(support.BASE);p.update(submission_kind='訂正報告',correction_reason='架空訂正')
  self.assertEqual(self.c.write(p)['record_version'],2)
  self.assertEqual(self.call('inspect',{})['audits'],2)
if __name__=='__main__':unittest.main()

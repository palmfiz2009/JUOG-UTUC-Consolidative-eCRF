"""A complete recovery listing must include locally bound requests."""
import copy,unittest
import test_recoverable_client as support
from recoverable_client import BridgeError

class JournalCompletenessTests(unittest.TestCase):
 setUp=support.T.setUp
 tearDown=support.T.tearDown
 call=support.T.call
 def missing(self,partial):
  self.drop=False;self.c.read();self.c.write(copy.deepcopy(support.BASE));self.c.read()
  correction=copy.deepcopy(support.BASE)
  correction.update(submission_kind='訂正報告',correction_reason='架空の訂正理由')
  if partial:
   self.c.write(correction);self.c.read()
   correction['correction_reason']='架空の次回訂正理由'
  before=self.call('inspect',{});original=self.c.transport
  prepare_count=self.calls.count('prepare_request')
  execute_count=self.calls.count('execute_request')
  def incomplete(a,p):
   response=original(a,p)
   if a=='list_requests':response['requests']=response['requests'][1:]
   return response
  self.c.transport=incomplete
  with self.assertRaisesRegex(BridgeError,'^RECOVERY_JOURNAL_INCOMPLETE$'):
   self.c.write(correction)
  self.assertEqual(self.calls.count('prepare_request'),prepare_count)
  self.assertEqual(self.calls.count('execute_request'),execute_count)
  self.assertEqual(self.call('inspect',{}),before)
 def test_entire_known_journal_missing(self):self.missing(False)
 def test_one_known_request_missing(self):self.missing(True)

if __name__=='__main__':unittest.main()

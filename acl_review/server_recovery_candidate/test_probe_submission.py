"""Read-only committed-record metadata must bind before content fields are omitted."""
import copy, unittest
from unittest.mock import patch
import test_recoverable_client as support
from test_bridge import native
import readonly_probe as m

class ProbeSubmissionTests(unittest.TestCase):
 setUp=support.T.setUp
 tearDown=support.T.tearDown
 call=support.T.call
 def mismatch(self,mutate):
  self.drop=False;self.c.read();self.c.write(copy.deepcopy(support.BASE))
  before=self.call('inspect',{});self.calls.clear()
  cfg=dict(approved=True,candidate_sha256=m.SHA,scope=dict(m.SCOPE),write_approved=False,review_ref='OFFLINE',starts_at=1000,expires_at=2800)
  def transport(envelope):
   action,payload=envelope;response=self.call(action,payload)
   if action=='read_crf':mutate(response['result']['records'][0])
   return response
  with patch.object(m,'signed_request',lambda n,a,p:(a,p)):
   with self.assertRaisesRegex(PermissionError,'^COMMITTED_SUBMISSION_MISMATCH$'):
    m.probe(lambda:native,transport,cfg,lambda:1001)
  self.assertEqual(self.calls,['list_requests','request_status','read_crf'])
  self.assertEqual(self.call('inspect',{}),before)
 def test_nested_submission_changed(self):
  self.mismatch(lambda r:r['payload'].update(submission_id='OTHER-OFFLINE-SUBMISSION'))
 def test_nested_submission_missing(self):
  self.mismatch(lambda r:r['payload'].pop('submission_id'))
 def test_transaction_changed(self):
  self.mismatch(lambda r:r.update(transaction_id='OTHER-OFFLINE-TRANSACTION'))
 def test_transaction_missing(self):
  self.mismatch(lambda r:r.pop('transaction_id'))

if __name__=='__main__':unittest.main()

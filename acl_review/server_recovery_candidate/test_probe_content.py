"""Bind read-only probe content to the actual offline GAS request fingerprint."""
import copy,unittest
from unittest.mock import patch
import test_recoverable_client as support
from test_bridge import native
import readonly_probe as m

class ProbeContentTests(unittest.TestCase):
 setUp=support.T.setUp
 tearDown=support.T.tearDown
 call=support.T.call
 def check_content(self,corrupt):
  self.drop=False;self.c.read();self.c.write(copy.deepcopy(support.BASE))
  before=self.call('inspect',{});self.calls.clear()
  cfg=dict(approved=True,candidate_sha256=m.SHA,scope=dict(m.SCOPE),write_approved=False,review_ref='OFFLINE',starts_at=1000,expires_at=2800)
  def transport(envelope):
   action,payload=envelope;response=self.call(action,payload)
   if action=='read_crf' and corrupt:corrupt(response['result']['records'][0]['payload'])
   return response
  with patch.object(m,'signed_request',lambda n,a,p:(a,p)):
   if corrupt:
    with self.assertRaisesRegex(PermissionError,'^COMMITTED_CONTENT_MISMATCH$'):
     m.probe(lambda:native,transport,cfg,lambda:1001)
   else:
    result=m.probe(lambda:native,transport,cfg,lambda:1001)
    self.assertEqual(result['latest_version'],1)
    self.assertTrue(result['manual_submission_content_audit_reconciliation_required'])
    self.assertNotIn('pathology',str(result))
  self.assertEqual(self.calls,['list_requests','request_status','read_crf'])
  self.assertEqual(self.call('inspect',{}),before)
 def test_matching_actual_domain_content(self):self.check_content(None)
 def test_changed_clinical_value(self):
  self.check_content(lambda p:p['data']['pathology'].update(size_mm=987654))
 def test_added_identifier_marker_not_hidden_by_redaction(self):
  self.check_content(lambda p:p['data'].update(patient_name='OFFLINE_FICTIONAL_MARKER'))

if __name__=='__main__':unittest.main()

import sys,unittest,copy
from pathlib import Path
from unittest.mock import patch
P=Path(__file__).parent
sys.path[:0]=[str(P),str(P.parent/'canonical_v9_integration')]
import readonly_probe as m

class Binding(unittest.TestCase):
 def run_probe(self,requests,records):
  calls=[]
  cfg=dict(approved=True,candidate_sha256=m.SHA,scope=dict(m.SCOPE),write_approved=False,review_ref='OFFLINE',starts_at=1000,expires_at=2800)
  def transport(e):
   a,p=e;calls.append(a)
   if a=='list_requests':return dict(ok=True,read_only=True,record_key=m.SCOPE['record_key'],requests=requests)
   if a=='request_status':
    q=next(r for r in requests if r['operation_id']==p['operation_id'])
    return dict(ok=True,action='save_crf',operation_id=q['operation_id'],state=q['state'],phase=q['phase'])
   return dict(ok=True,read_only=True,result=dict(ok=True,records=records))
  with patch.object(m,'signed_request',lambda n,a,p:(a,p)):
   return m.probe(lambda:None,transport,cfg,lambda:1001),calls
 def data(self):
  q=dict(operation_id='fake-op',submission_id='fake-sub',state='SAVED',phase='COMMITTED',expected_record_version=0,content_sha256='a'*64)
  r=dict(record_key=m.SCOPE['record_key'],record_version=1,submission_id='fake-sub',payload=dict(registration_id='JUOG-971',facility_code='TEST01',crf_type='perioperative_30d',visit='30d',clinical='FICTIONAL_PRIVATE_MARKER'))
  return q,r
 def test_good_binding_no_raw_data(self):
  q,r=self.data();result,calls=self.run_probe([q],[r])
  self.assertEqual(calls,['list_requests','request_status','read_crf'])
  self.assertEqual(result['latest_version'],1)
  for secret in ['fake-sub','fake-op','FICTIONAL_PRIVATE_MARKER']:self.assertNotIn(secret,str(result))
 def test_committed_mismatch(self):
  q,r=self.data()
  for delta in [{'submission_id':'missing'},{'expected_record_version':1}]:
   with self.subTest(delta=delta),self.assertRaisesRegex(PermissionError,'COMMITTED_RECORD_MISMATCH'):self.run_probe([q|delta],[r])
 def test_duplicate_record_submission(self):
  q,r=self.data()
  with self.assertRaisesRegex(PermissionError,'DUPLICATE_SUBMISSION'):self.run_probe([q],[r,r|{'record_version':2}])
 def test_duplicate_request_submission(self):
  q,r=self.data()
  with self.assertRaisesRegex(PermissionError,'REQUESTS_UNVERIFIABLE'):self.run_probe([q,q|{'operation_id':'other'}],[r])
 def test_invalid_expected_version(self):
  q,r=self.data()
  for base in [None,True,-1,'0',0.5]:
   with self.subTest(base=base),self.assertRaisesRegex(PermissionError,'REQUEST_METADATA_INVALID'):self.run_probe([q|{'expected_record_version':base}],[r])
 def test_noncommitted_cannot_have_record(self):
  q,r=self.data()
  for state,phase in [('FAILED','REJECTED_BEFORE_INTENT'),('UNFINISHED','PREPARED')]:
   with self.assertRaisesRegex(PermissionError,'REQUEST_RECORD_STATE_MISMATCH'):self.run_probe([q|dict(state=state,phase=phase)],[r])
 def test_bad_shape_is_safe_error(self):
  q,r=self.data()
  with self.assertRaisesRegex(PermissionError,'REQUESTS_UNVERIFIABLE'):self.run_probe(['FICTIONAL_PRIVATE_MARKER'],[r])
 def test_legacy_without_request_still_requires_manual_reconciliation(self):
  q,r=self.data();result,_=self.run_probe([],[r])
  self.assertTrue(result['manual_submission_content_audit_reconciliation_required'])

if __name__=='__main__':unittest.main()

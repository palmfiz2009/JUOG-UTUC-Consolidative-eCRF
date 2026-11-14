import sys,unittest
from pathlib import Path
from unittest.mock import patch
P=Path(__file__).parent
sys.path.insert(0,str(P.parent/'canonical_v9_integration'))
import readonly_probe as m
class Test(unittest.TestCase):
 def config(self):return dict(approved=True,candidate_sha256=m.SHA,scope=dict(m.SCOPE),write_approved=False,review_ref='OFFLINE',starts_at=1000,expires_at=2800)
 def test_denied_configs(self):
  for delta in [dict(approved=False),dict(write_approved=True),dict(expires_at=2801),dict(scope={}),dict(review_ref=''),dict(candidate_sha256='bad')]:
   with self.assertRaises(PermissionError):m.gate(self.config()|delta,1000)
 def test_boundary(self):
  m.gate(self.config(),2799)
  with self.assertRaises(PermissionError):m.gate(self.config(),2800)
 def test_read_calls_only_metadata(self):
  calls=[]
  def transport(e):
   a,p=e;calls.append(a)
   if a=='list_requests':return dict(ok=True,read_only=True,record_key=m.SCOPE['record_key'],requests=[dict(operation_id='fake-op',submission_id='fake-sub',state='SAVED',phase='COMMITTED',content_sha256='a'*64)])
   if a=='request_status':return dict(ok=True,operation_id='fake-op',action='save_crf',state='SAVED',phase='COMMITTED')
   return dict(ok=True,read_only=True,result=dict(ok=True,records=[dict(record_version=v,record_key=m.SCOPE['record_key'],submission_id='fake-sub',payload=dict(registration_id='JUOG-971',facility_code='TEST01',crf_type='perioperative_30d',visit='30d',clinical='PRIVATE')) for v in (1,2)]))
  with patch.object(m,'signed_request',lambda n,a,p:(a,p)):
   r=m.probe(lambda:object(),transport,self.config(),lambda:1001)
  self.assertEqual(calls,['list_requests','request_status','read_crf']);self.assertEqual(r['latest_version'],2);self.assertNotIn('PRIVATE',str(r));self.assertNotIn('fake-sub',str(r))
 def test_foreign_or_failed_records_rejected(self):
  valid=dict(record_version=1,record_key=m.SCOPE['record_key'],submission_id='fake-sub',payload=dict(registration_id='JUOG-971',facility_code='TEST01',crf_type='perioperative_30d',visit='30d'))
  for inner in [dict(ok=False,records=[valid]),dict(ok=True,records=[valid|{'record_key':'OTHER'}]),dict(ok=True,records=[valid|{'payload':valid['payload']|{'facility_code':'OTHER'}}])]:
   def transport(e):
    if e[0]=='list_requests':return dict(ok=True,read_only=True,record_key=m.SCOPE['record_key'],requests=[])
    return dict(ok=True,read_only=True,result=inner)
   with patch.object(m,'signed_request',lambda n,a,p:(a,p)),self.assertRaises(PermissionError):m.probe(lambda:None,transport,self.config(),lambda:1001)
 def test_untrusted_metadata_rejected(self):
  for row in [dict(operation_id='o',submission_id='s',state='RAW_SECRET',phase='RAW',content_sha256='a'*64),dict(operation_id='o',submission_id='s',state='SAVED',phase='COMMITTED',content_sha256='untrusted')]:
   with patch.object(m,'signed_request',lambda n,a,p:(a,p)),self.assertRaises(PermissionError):m.probe(lambda:None,lambda e:dict(ok=True,read_only=True,record_key=m.SCOPE['record_key'],requests=[row]),self.config(),lambda:1001)
 def test_expired_never_transports(self):
  with self.assertRaises(PermissionError):m.probe(lambda:None,lambda e:self.fail(),self.config(),lambda:2800)
if __name__=='__main__':unittest.main()

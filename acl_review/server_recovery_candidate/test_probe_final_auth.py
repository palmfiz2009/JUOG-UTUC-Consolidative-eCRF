"""The final read response must not outlive the native authentication context."""
import copy,json,sys,time,unittest
from pathlib import Path
P=Path(__file__).parent
sys.path[:0]=[str(P),str(P.parent/'canonical_v9_integration')]
import readonly_probe as m
from test_bridge import native

class FinalAuthTests(unittest.TestCase):
 def run_change(self,change,error):
  current=copy.deepcopy(native);calls=[]
  cfg=dict(approved=True,candidate_sha256=m.SHA,scope=dict(m.SCOPE),write_approved=False,review_ref='OFFLINE',starts_at=1000,expires_at=2800)
  def transport(envelope):
   action=json.loads(envelope['request_json'])['action'];calls.append(action)
   if action=='list_requests':return dict(ok=True,read_only=True,record_key=m.SCOPE['record_key'],requests=[])
   change(current)
   return dict(ok=True,read_only=True,result=dict(ok=True,records=[dict(record_version=1,record_key=m.SCOPE['record_key'],submission_id='OFFLINE-LEGACY',payload=dict(registration_id='JUOG-971',facility_code='TEST01',crf_type='perioperative_30d',visit='30d'))]))
  with self.assertRaisesRegex(PermissionError,'^'+error+'$'):
   m.probe(lambda:current,transport,cfg,lambda:1001)
  self.assertEqual(calls,['list_requests','read_crf'])
 def test_switch_during_final_response(self):
  self.run_change(lambda n:n.user.update(sub='OFFLINE-OTHER'), 'PROBE_PRINCIPAL_CHANGED')
 def test_logout_during_final_response(self):
  self.run_change(lambda n:setattr(n.user,'is_logged_in',False), 'INDIVIDUAL_LOGIN_REQUIRED')
 def test_expiry_during_final_response(self):
  self.run_change(lambda n:n.user.update(exp=int(time.time())-1), 'OIDC_TOKEN_EXPIRED_OR_MISSING')

if __name__=='__main__':unittest.main()

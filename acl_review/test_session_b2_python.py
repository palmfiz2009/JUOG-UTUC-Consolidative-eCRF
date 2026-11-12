import base64,json,sys,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).parent/'python_candidate'))
from auth_bridge import signed_request
from app_session_b import policy_logout
class User(dict): is_logged_in=True
class B2(unittest.TestCase):
 def setUp(self):
  self.u=User(iss='https://idp.invalid',sub='SYNTHETIC',aud='client',iat=1000,exp=9000,nonce='synthetic-nonce')
  self.c=dict(oidc_issuer=self.u['iss'],oidc_client_id='client',signing_key='x'*40,bridge_issuer='local',audience='localgas',session_policy='isolated_gas_session_b2',session_environment='JUOG_AUTH04_ISOLATED_TEST01',session_b_safety_review_approved=True,session_b_limited_execution_approved=True,session_store_generation='synthetic-generation')
  self.events=[];self.st=SimpleNamespace(user=self.u,secrets={'juog_identity_bridge':self.c},logout=lambda:self.events.append('logout'))
 def sign(self):
  with patch('auth_bridge.time.time',return_value=1100): r=signed_request(self.st,'ui_context',{})
  b=r['identity_assertion'].split('.')[0];return json.loads(base64.urlsafe_b64decode(b+'='*(-len(b)%4)))
 def test_no_local_store_needed_and_15_second_assertion(self):
  a=self.sign();self.assertEqual(a['v'],2);self.assertEqual(a['exp'],1115);self.assertEqual(a['session']['deadline'],4600)
 def test_two_workers_same_session_unique_request(self):
  a,b=self.sign(),self.sign();self.assertEqual(a['session']['sid'],b['session']['sid']);self.assertNotEqual(a['session']['jti'],b['session']['jti'])
 def test_missing_nonce_denied(self):
  del self.u['nonce']
  with self.assertRaises(PermissionError):self.sign()
 def test_approval_missing_denied(self):
  self.c['session_b_limited_execution_approved']=False
  with self.assertRaises(PermissionError):self.sign()
 def test_remote_revoke_ack_before_logout(self):
  with patch('time.time',return_value=1100),patch('streamlit_unified_client._post',return_value={'ok':True,'revoked':True}) as p:policy_logout(self.st)
  self.assertEqual(p.call_args.args[1],'session_revoke');self.assertEqual(self.events,['logout'])
 def test_revoke_timeout_no_cookie_only_logout(self):
  with patch('time.time',return_value=1100),patch('streamlit_unified_client._post',side_effect=TimeoutError):
   with self.assertRaises(TimeoutError):policy_logout(self.st)
  self.assertEqual(self.events,[])
if __name__=='__main__':unittest.main(verbosity=2)

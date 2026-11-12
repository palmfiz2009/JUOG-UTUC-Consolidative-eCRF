import sys,unittest
from types import SimpleNamespace
from unittest.mock import patch
sys.modules.setdefault('streamlit',SimpleNamespace())
import uat_auth_connect as a
class User(dict):is_logged_in=True
class Stop(BaseException):pass
class Fake:
 def __init__(self,expired=False):
  self.user=User(iat=1,exp=2) if expired else User(iat=1000,exp=2000)
  self.session_state={};self.logged_out=False
 def __getattr__(self,n):return lambda *args,**kwargs:None
 def button(self,name):return name in ['本人ACLと拒否条件を実測','期限切れのログインを終了して再認証']
 def stop(self):raise Stop()
 def logout(self):self.logged_out=True
class Tests(unittest.TestCase):
 def test_config_pins(self):
  cfg={'enabled':True,'review_approved':True,'stage':'AUTH_CONNECT','url':a.URL,'session_store_generation':a.GENERATION,'signing_key':'x'*40}
  st=SimpleNamespace(secrets={'auth_connect':cfg,'auth':{'google':{'client_id':'client'}}},user=User())
  with patch.object(a,'identity_proposal',return_value={'principal_fingerprint':a.FINGERPRINT}):
   self.assertEqual(a.context(st).secrets['juog_identity_bridge']['session_policy'],'isolated_gas_session_b2')
   for k,v in [('enabled',False),('review_approved',False),('stage','AUTH04_APPROVED'),('url','https://other.invalid'),('session_store_generation','bad')]:
    old=cfg[k];cfg[k]=v
    with self.assertRaises(PermissionError):a.context(st)
    cfg[k]=old
 def test_other_principal_denied(self):
  st=SimpleNamespace(secrets={'auth_connect':dict(enabled=True,review_approved=True,stage='AUTH_CONNECT',url=a.URL,session_store_generation=a.GENERATION),'auth':{'google':{'client_id':'client'}}},user=User())
  with patch.object(a,'identity_proposal',return_value={'principal_fingerprint':'other'}):
   with self.assertRaises(PermissionError):a.context(st)
 def test_unexpected_response_stops_after_one_request(self):
  f=Fake()
  with patch.object(a,'st',f),patch.object(a,'context',return_value=object()),patch.object(a,'send',return_value={'ok':True}) as send:
   with self.assertRaises(Stop):a.run()
   self.assertEqual(send.call_count,1);self.assertTrue(f.session_state['auth_connect_halted'])
 def test_expired_cookie_can_log_out_without_request(self):
  f=Fake(True)
  with patch.object(a,'st',f),patch.object(a,'context',side_effect=PermissionError),patch.object(a,'send') as send:
   with self.assertRaises(Stop):a.run()
   self.assertTrue(f.logged_out);send.assert_not_called()
 def test_active_cookie_not_cleared_on_config_error(self):
  f=Fake();f.user['iat']=int(a.time.time());f.user['exp']=int(a.time.time())+3600
  with patch.object(a,'st',f),patch.object(a,'context',side_effect=PermissionError),patch.object(a,'send') as send:
   with self.assertRaises(Stop):a.run()
   self.assertFalse(f.logged_out);send.assert_not_called()
 def test_context_response_requires_facility_scope(self):
  r=dict(ok=True,role='facility',facilities=['TEST01'],facility_code='TEST01',execution_stage='AUTH_CONNECT',business_writes_allowed=False)
  self.assertTrue(a.valid_context(r));r['role']='admin';self.assertFalse(a.valid_context(r))
if __name__=='__main__':unittest.main()

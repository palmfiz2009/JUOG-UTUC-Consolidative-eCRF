import ast,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
src=Path(__file__).with_name('streamlit_app.py').read_text()
tree=ast.parse(src);tree.body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('expired_native_login','safe_logout')]
class LogoutTest(unittest.TestCase):
 def run_case(self,expiry=2000,result=None,fail=False):
  events=[]; ns={'time':SimpleNamespace(time=lambda:1000),'context':lambda st:events.append('context') or st,'send':lambda req:events.append('revoke') or result}
  def sign(st,action,payload):
   self.assertEqual((action,payload),('session_revoke',{}))
   if fail:raise PermissionError('denied')
   return {}
  exec(compile(tree,'candidate','exec'),ns)
  st=SimpleNamespace(user={'iat':900,'exp':expiry},logout=lambda:events.append('logout'))
  with patch.dict('sys.modules',{'uat_b2_auth_bridge':SimpleNamespace(signed_request=sign)}):
   try:ns['safe_logout'](st)
   except PermissionError:events.append('stopped')
  return events
 def test_live_revoked_then_logout(self):self.assertEqual(self.run_case(result={'ok':True,'revoked':True}),['context','revoke','logout'])
 def test_denied_no_logout(self):self.assertEqual(self.run_case(result={'ok':False}),['context','revoke','stopped'])
 def test_missing_revoked_no_logout(self):self.assertEqual(self.run_case(result={'ok':True}),['context','revoke','stopped'])
 def test_expired_no_send(self):self.assertEqual(self.run_case(expiry=999),['logout'])
 def test_signer_denial_no_send(self):self.assertEqual(self.run_case(fail=True),['context','stopped'])
 def test_no_halt_clear_or_business(self):
  function=next(n for n in tree.body if n.name=='safe_logout');code=ast.unparse(function)
  for token in ('prepare','execute','save_crf','session_state'):self.assertNotIn(token,code)
if __name__=='__main__':unittest.main()

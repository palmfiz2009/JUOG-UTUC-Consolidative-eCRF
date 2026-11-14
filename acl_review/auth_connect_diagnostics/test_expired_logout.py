import unittest,ast
from pathlib import Path
from auth_diagnostics import expired_native_login
class T(unittest.TestCase):
 def test_expiry_only(self):
  self.assertFalse(expired_native_login({'iat':100,'exp':7300},3699));self.assertTrue(expired_native_login({'iat':100,'exp':7300},3700));self.assertTrue(expired_native_login({'iat':100,'exp':200},200))
 def test_malformed_never_offers(self):
  for u in [{},{'iat':'100','exp':7300},{'iat':True,'exp':7300},{'iat':4000,'exp':7300},{'iat':100,'exp':90}]:self.assertFalse(expired_native_login(u,3700))
 def test_halt_branch_only_logout_no_network_or_clear(self):
  tree=ast.parse(Path(__file__).with_name('streamlit_app.py').read_text());branch=next(n for n in ast.walk(tree) if isinstance(n,ast.If) and 'auth_connect_halted' in ast.unparse(n.test))
  calls=[ast.unparse(n.func) for n in ast.walk(branch) if isinstance(n,ast.Call)]
  self.assertIn('st.logout',calls);self.assertIn('st.stop',calls);self.assertNotIn('send',calls);self.assertNotIn('context',calls);self.assertFalse(any(isinstance(n,(ast.Assign,ast.Delete)) for n in ast.walk(branch)))
if __name__=='__main__':unittest.main()

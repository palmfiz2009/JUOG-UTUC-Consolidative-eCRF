import ast,sys,types,unittest,runpy,time
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).parent
class Stop(Exception):pass
class Entry(unittest.TestCase):
 def invoke(self,logged=True,context_ok=True,acl_ok=True,halted=False):
  calls=[];st=types.ModuleType('streamlit');st.user=types.SimpleNamespace(is_logged_in=logged,get=lambda k:int(time.time())+3600);st.session_state={'auth_connect_halted':halted}
  for k in ['set_page_config','title','info','error','success','caption','warning']:setattr(st,k,lambda *a,**kw:None)
  st.checkbox=lambda *a:True;st.button=lambda *a:False
  def stop():raise Stop()
  st.stop=stop;b=types.ModuleType('uat_auth_connect')
  def context(s):
   calls.append('context')
   if not context_ok:raise PermissionError()
   return object()
  b.context=context;b.context_envelope=lambda c:{};b.send=lambda e:(calls.append('signed_context') or {'ok':acl_ok});b.valid_context=lambda r:r['ok']
  with patch.dict(sys.modules,{'streamlit':st,'uat_auth_connect':b}),patch.object(runpy,'run_path',lambda *a,**kw:calls.append('render')):
   try:exec(compile((ROOT/'streamlit_app.py').read_text(),'entry','exec'),{'__file__':str(ROOT/'streamlit_app.py')})
   except Stop:pass
  return calls
 def test_auth_order(self):self.assertEqual(self.invoke(),['context','signed_context','render'])
 def test_unauth_no_render(self):self.assertEqual(self.invoke(logged=False),[])
 def test_invalid_context_no_render(self):self.assertEqual(self.invoke(context_ok=False),['context'])
 def test_revoked_acl_no_render(self):self.assertEqual(self.invoke(acl_ok=False),['context','signed_context'])
 def test_halted_no_render(self):self.assertEqual(self.invoke(halted=True),[])
 def test_each_rerun_checks_acl(self):
  self.assertEqual(self.invoke().count('signed_context'),1);self.assertEqual(self.invoke().count('signed_context'),1)
class Boundary(unittest.TestCase):
 def test_business_preview_or_denied_never_http(self):
  import juog_common as c
  with patch('urllib.request.urlopen',side_effect=AssertionError('NETWORK_FORBIDDEN')):
   for a in ['validate','read_crf','save_crf','save_draft','get_draft','delete_draft','get_crf_linkage','unknown']:
    self.assertFalse(c.registry_call(a,{}).get('ok'))
   self.assertEqual(c._smtp_send('synthetic','synthetic',[]),(False,'UAT_EMAIL_DISABLED'))
 def test_save_buttons_disabled(self):
  tree=ast.parse((ROOT/'02_perioperative_30d_crf.py').read_text())
  found=[]
  for n in ast.walk(tree):
   if isinstance(n,ast.Call):
    kw={x.arg:x.value for x in n.keywords}
    if isinstance(kw.get('key'),ast.Constant) and kw['key'].value in ['draft30_save_button','draft30_load_button','draft30_submit_button']:
     self.assertIs(kw['disabled'].value,True);found.append(kw['key'].value)
  self.assertEqual(len(found),3)
if __name__=='__main__':unittest.main()

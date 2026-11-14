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
class NetworkBlock(unittest.TestCase):
 def test_all_business_routes_no_network(self):
  import juog_readonly_common as c
  with patch('urllib.request.urlopen',side_effect=AssertionError('NETWORK_FORBIDDEN')):
   for a in ['validate','read_crf','save_crf','save_draft','get_draft','delete_draft','get_crf_linkage','unknown']:
    self.assertEqual(c.registry_call(a,{}),{'ok':False,'error':'AUTH_CONNECT_BUSINESS_DISABLED'})
   self.assertEqual(c._smtp_send('synthetic','synthetic',[]),(False,'UAT_EMAIL_DISABLED'))
 def test_page_changes_only_import_and_disabled_buttons(self):
  import subprocess
  old=subprocess.check_output(['git','-C',str(ROOT.parents[1]),'show','dc2632f:02_perioperative_30d_crf.py'],text=True)
  old=old.replace('from juog_common import (','from juog_readonly_common import (').replace('key="draft30_save_button", disabled=False','key="draft30_save_button", disabled=True').replace('key="draft30_load_button", use_container_width=True','key="draft30_load_button", use_container_width=True, disabled=True').replace('disabled=L, key="draft30_submit_button"','disabled=True, key="draft30_submit_button"')
  start=old.index('if "peri_sent" not in st.session_state:');end=old.index('draft_tool_col1,',start);old=old[:start]+old[end:]
  old=old.replace('peri_','inspect_peri_').replace('draft30_','inspect_draft30_')
  old=old.replace('        else:\n            path["ypn"] = "ypNX（郭清なし）"','        elif ln_dissection == "実施しなかった":\n            path["ypn"] = "ypNX（郭清なし）"').replace('        # 術後病理で確認された検索リンパ節数。','        else:\n            path["ypn"] = ""\n            st.info("リンパ節郭清の実施有無を選択してください。")\n        # 術後病理で確認された検索リンパ節数。')
  old=old.replace('else:\n    st.info("手術未施行のため病理項目はN/Aです。")','elif surgery_performed == "実施しなかった":\n    st.info("手術未施行のため病理項目はN/Aです。")\nelse:\n    st.info("手術実施有無が未選択のため、病理の適用可否は未確定です。")')
  self.assertEqual(old,(ROOT/'uat_readonly_30d.py').read_text())
if __name__=='__main__':unittest.main()

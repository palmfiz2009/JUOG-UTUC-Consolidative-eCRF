import runpy,sys,time,types,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
class Stop(BaseException):pass
class Entry(unittest.TestCase):
 def execute(self,logged=True,approved=True,allowed=True,halted=False,logout=False,revoked=True,error=None,open_recovery=False):
  events=[];st=types.ModuleType('streamlit')
  st.user=types.SimpleNamespace(is_logged_in=logged,get=lambda k:int(time.time()) if k=='iat' else int(time.time())+7200)
  st.session_state={'auth_connect_halted':halted,'_integration_edit_subject':'JUOG-901'}
  if open_recovery:st.session_state.update(_recovery_open=True,_recovery_blocks_new=True)
  for n in ['set_page_config','title','caption','info','error']:setattr(st,n,lambda *a,**k:None)
  st.stop=lambda:(_ for _ in ()).throw(Stop())
  st.button=lambda label:(logout and label=='セッションを失効してログアウト') or (open_recovery and label=='保存状態の照合・復旧を開く')
  st.selectbox=lambda *a,**k:'30日';st.text_input=lambda *a,**k:'JUOG-901'
  st.logout=lambda:events.append('logout')
  adapter=types.ModuleType('isolated_crf_adapter')
  def context(st):
   events.append('native')
   if not approved:raise PermissionError()
  def call(st,a,p):
   events.append(a)
   return {'ok':allowed,'business_writes_allowed':allowed,'revoked':revoked,'error':error}
  adapter.context=context;adapter.call=call;adapter.begin_edit=lambda *a:None
  recovery=types.ModuleType('isolated_recovery_ui');recovery.render=lambda ui:events.append(('recovery',ui.session_state.get('_recovery_open')))
  with patch.dict(sys.modules,{'streamlit':st,'isolated_crf_adapter':adapter,'isolated_recovery_ui':recovery}),patch.object(runpy,'run_path',side_effect=lambda *a,**k:events.append('render')):
   try:exec(compile((ROOT/'streamlit_app.py').read_text(),'entry','exec'),{'__file__':str(ROOT/'streamlit_app.py')})
   except Stop:pass
   except NameError as e:
    # __file__ is required for dispatch; never skip render assertion.
    raise
  self.state=st.session_state
  return events
 def test_unauthenticated_no_form(self):self.assertEqual(self.execute(logged=False),[])
 def test_unapproved_no_network_or_form(self):self.assertEqual(self.execute(approved=False),['native'])
 def test_acl_denied_no_form(self):self.assertEqual(self.execute(allowed=False),['native','ui_context'])
 def test_halted_no_form(self):self.assertEqual(self.execute(halted=True),[])
 def test_signed_revoke_before_logout(self):self.assertEqual(self.execute(logout=True),['session_revoke','logout'])
 def test_failed_revoke_does_not_logout(self):self.assertEqual(self.execute(logout=True,revoked=False),['session_revoke'])
 def test_auth_before_form(self):self.assertEqual(self.execute(),['native','ui_context','render'])
 def test_transient_connection_stops_form_without_revoking_identity(self):
  self.assertEqual(self.execute(allowed=False,error='RESULT_UNCONFIRMED'),['native','ui_context'])
  self.assertTrue(self.state['_connection_unconfirmed'])
  self.assertFalse(self.state['auth_connect_halted'])
  self.assertEqual(self.state['_integration_edit_subject'],'JUOG-901')
 def test_expired_assertion_recheck_keeps_form_closed_and_input_identity(self):
  self.assertEqual(self.execute(allowed=False,error='ASSERTION_RECONFIRMATION_REQUIRED'),['native','ui_context'])
  self.assertTrue(self.state['_connection_unconfirmed'])
  self.assertFalse(self.state['auth_connect_halted'])
  self.assertEqual(self.state['_integration_edit_subject'],'JUOG-901')
 def test_actual_acl_denial_still_halts(self):
  self.execute(allowed=False,error='ACL_DENIED')
  self.assertTrue(self.state['auth_connect_halted'])

 def test_reopening_recovery_requires_explicit_target_check_without_clearing_safety_gate(self):
  self.assertEqual(self.execute(open_recovery=True),['native','ui_context',('recovery',False)])
  self.assertTrue(self.state['_recovery_blocks_new'])

if __name__=='__main__':unittest.main()

import ast,copy,hashlib,importlib,json,sys,time,types,unittest,urllib.error,uuid
from pathlib import Path
from unittest.mock import Mock,patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));import resume_checkpoint_candidate
SOURCE=ROOT/'uat_b971_continuation.py';CP=json.loads((ROOT/'b971_checkpoint.json').read_bytes())
class Stop(BaseException):pass
class User(dict):is_logged_in=True
class UI:
 def __init__(self,state=None,button=''):
  self.session_state=state or {};self.user=User(iat=1000,exp=9000);self.secrets={};self.target=button;self.logout=Mock()
 def button(self,name):return name==self.target
 def stop(self):raise Stop()
 def __getattr__(self,name):return lambda *args,**kwargs:None
def module():
 ns=dict(__file__=str(SOURCE),Path=Path,copy=copy,hashlib=hashlib,json=json,time=time,uuid=uuid,urllib=urllib,SimpleNamespace=types.SimpleNamespace,CASE='JUOG-971',FACILITY='TEST01',FIXTURE_PATH=ROOT/'uat_auth04_fixture.json',WRITE_ACTIONS={'save_crf','save_draft'},READ_ACTIONS={'ui_context','get_draft','read_crf'},LIFECYCLE={'prepare_request','execute_request','request_status'},PAIRS={('perioperative_30d','30d'),('day90','90d'),('followup','6m')},PREPARE_MIN_REMAINING_SECONDS=900)
 for n in ast.parse(SOURCE.read_text()).body:
  if isinstance(n,(ast.FunctionDef,ast.ClassDef)) or (isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ('CHECKPOINT_SHA','VERIFIER_SHA') for t in n.targets)):exec(compile(ast.Module(body=[n],type_ignores=[]),'exact-continuation-functions','exec'),ns)
 return ns
class Tests(unittest.TestCase):
 def setUp(self):
  self.ns=module();self.verify=Mock(return_value=(4,CP['evidence_ref']));self.ns.update(native_context=Mock(),context=Mock(),call=Mock(return_value={'ok':True}),b971_history=Mock(return_value=[]))
 def restore(self,ui):
  with patch.object(importlib,'reload',return_value=types.SimpleNamespace(verify_checkpoint=self.verify)):return self.ns['restore_verified_checkpoint'](ui)
 def test_all_source_and_data_pins_match(self):
  self.assertIn(hashlib.sha256(SOURCE.read_bytes()).hexdigest(),(ROOT/'streamlit_app_continuation.py').read_text())
  self.assertEqual(self.ns['CHECKPOINT_SHA'],hashlib.sha256((ROOT/'b971_checkpoint.json').read_bytes()).hexdigest())
  self.assertEqual(self.ns['VERIFIER_SHA'],hashlib.sha256((ROOT/'resume_checkpoint_candidate.py').read_bytes()).hexdigest())
 def test_readonly4statuses3histories_and_no_input_state_changes(self):
  ui=UI({'sentinel':[1]});before=copy.deepcopy(ui.session_state);self.assertEqual(self.restore(ui)[0],4);self.assertEqual(ui.session_state,before)
  self.assertEqual(self.ns['call'].call_count,4);self.assertEqual(self.ns['b971_history'].call_count,3)
  self.assertTrue(all(c.args[1]=='request_status' for c in self.ns['call'].call_args_list));self.ns['context'].assert_called_once();self.verify.assert_called_once()
  self.assertEqual([c.args[2]['operation_id'] for c in self.ns['call'].call_args_list],[p['operation_id'] for p in CP['completed']])
 def test_pending_and_uncertain_refuse_before_reads(self):
  for state in [{'auth04_pending':'pending'},{'auth04_preparation_uncertain':True}]:
   with self.assertRaises(PermissionError):self.restore(UI(state))
  self.ns['native_context'].assert_not_called();self.ns['call'].assert_not_called()
 def test_wrong_checkpoint_hash_refuses_without_read(self):
  self.ns['CHECKPOINT_SHA']='0'*64
  with self.assertRaises(PermissionError):self.restore(UI())
  self.ns['native_context'].assert_not_called()
 def test_wrong_verifier_hash_refuses_without_read(self):
  self.ns['VERIFIER_SHA']='0'*64
  with self.assertRaises(PermissionError):self.restore(UI())
  self.ns['native_context'].assert_not_called()
 def test_fresh_fixture_bytes_are_checked(self):
  self.ns['FIXTURE_PATH']=types.SimpleNamespace(read_bytes=lambda:b'{}')
  with self.assertRaises(PermissionError):self.restore(UI())
  self.ns['native_context'].assert_not_called()
 def test_auth_failure_does_not_mutate(self):
  ui=UI({'sentinel':[1]});before=copy.deepcopy(ui.session_state);self.ns['native_context'].side_effect=PermissionError()
  with self.assertRaises(PermissionError):self.restore(ui)
  self.assertEqual(ui.session_state,before);self.ns['call'].assert_not_called()
 def test_read_failure_does_not_mutate(self):
  ui=UI({'sentinel':[1]});before=copy.deepcopy(ui.session_state);self.ns['call'].side_effect=[{'ok':True},TimeoutError()]
  with self.assertRaises(TimeoutError):self.restore(ui)
  self.assertEqual(ui.session_state,before);self.verify.assert_not_called()
 def test_history_verification_failure_does_not_mutate(self):
  ui=UI({'sentinel':[1]});before=copy.deepcopy(ui.session_state);self.verify.side_effect=PermissionError()
  with self.assertRaises(PermissionError):self.restore(ui)
  self.assertEqual(ui.session_state,before)
 def test_no_cursor_rewind(self):
  ui=UI({'b971_step':5})
  with self.assertRaises(PermissionError):self.restore(ui)
  self.assertEqual(ui.session_state['b971_step'],5)
 def test_run_commits_cursor_only_after_success_no_fake_results(self):
  ui=UI();self.ns.update(st=ui,restore_verified_checkpoint=Mock(return_value=(4,'evidence')),require_prepare_window=Mock(side_effect=self.ns['PrepareWindowClosed']()))
  with self.assertRaises(Stop):self.ns['run']()
  self.assertEqual(ui.session_state,{'b971_step':4,'b971_checkpoint_evidence':'evidence'})
 def test_run_restore_failure_leaves_cursor_absent(self):
  ui=UI();self.ns.update(st=ui,restore_verified_checkpoint=Mock(side_effect=PermissionError()))
  with self.assertRaises(Stop):self.ns['run']()
  self.assertNotIn('b971_step',ui.session_state)
 def test_reauth_uses_confirmed_revoke_path(self):
  ui=UI({'b971_step':4},'checkpointを照合してログアウト・再認証へ');rev=Mock();self.ns.update(st=ui,restore_verified_checkpoint=Mock(return_value=(4,'evidence')),revoke_and_logout=rev,require_prepare_window=Mock(side_effect=self.ns['PrepareWindowClosed']()))
  with self.assertRaises(Stop):self.ns['run']()
  rev.assert_called_once_with(ui);ui.logout.assert_not_called()
 def test_revoke_failure_never_cookie_only_logout(self):
  ui=UI({'b971_step':4},'checkpointを照合してログアウト・再認証へ');self.ns.update(st=ui,restore_verified_checkpoint=Mock(return_value=(4,'evidence')),revoke_and_logout=Mock(side_effect=PermissionError()),require_prepare_window=Mock(side_effect=self.ns['PrepareWindowClosed']()))
  with self.assertRaises(Stop):self.ns['run']()
  ui.logout.assert_not_called()
if __name__=='__main__':unittest.main(verbosity=2)

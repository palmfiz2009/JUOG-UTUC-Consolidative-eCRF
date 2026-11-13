import ast,copy,hashlib,json,time,types,unittest,uuid,urllib.error
from pathlib import Path
from unittest.mock import Mock,patch
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'uat_b971_live.py'
class Stop(BaseException):pass
class UI:
 def __init__(self,state=None,button=''):
  self.session_state=state or {};self.user=types.SimpleNamespace(is_logged_in=True);self.target=button;self.calls=[]
 def button(self,name):self.calls.append(name);return name==self.target
 def stop(self):raise Stop()
 def __getattr__(self,name):return lambda *args,**kwargs:None
def module():
 ns=dict(copy=copy,hashlib=hashlib,json=json,time=time,uuid=uuid,urllib=urllib,Path=Path,CASE='JUOG-971',FACILITY='TEST01',FIXTURE_PATH=ROOT/'uat_auth04_fixture.json',WRITE_ACTIONS={'save_crf','save_draft'},READ_ACTIONS={'ui_context','get_draft','read_crf'},LIFECYCLE={'prepare_request','execute_request','request_status'},PAIRS={('perioperative_30d','30d'),('day90','90d'),('followup','6m')},PREPARE_MIN_REMAINING_SECONDS=900)
 for n in ast.parse(SOURCE.read_text()).body:
  if isinstance(n,(ast.FunctionDef,ast.ClassDef)):exec(compile(ast.Module(body=[n],type_ignores=[]),'exact-candidate-functions','exec'),ns)
 return ns
class Tests(unittest.TestCase):
 def setUp(self):self.ns=module();self.step=json.loads((ROOT/'uat_auth04_fixture.json').read_text())['steps'][0]
 def ui_run(self,state,button,call):
  ui=UI(state,button);self.ns.update(st=ui,native_context=Mock(),call=call)
  with self.assertRaises(Stop):self.ns['run']()
  return ui
 def test_entry_pin_matches(self):self.assertIn(hashlib.sha256(SOURCE.read_bytes()).hexdigest(),(ROOT/'streamlit_app.py').read_text())
 def test_wrong_case_or_facility_or_role_refused(self):
  for k,v in [('registration_id','JUOG-970'),('facility_code','TEST02'),('role','admin')]:
   p=copy.deepcopy(self.step['payload']);p[k]=v
   with self.assertRaises(PermissionError):self.ns['check_payload']('save_crf',p)
 def test_unknown_operation_never_signed(self):
  self.ns['native_context']=Mock()
  with self.assertRaises(PermissionError):self.ns['call'](UI(),'execute_request',{'operation_id':'unknown'})
  self.ns['native_context'].assert_not_called()
 def test_uncertain_execute_retains_operation_and_no_new_prepare(self):
  ui=UI();self.ns['context']=Mock();self.ns['call']=Mock(side_effect=[{'ok':True,'operation_id':'op'},TimeoutError()])
  with self.assertRaises(TimeoutError):self.ns['write_once'](ui,'save_crf',self.step['payload'])
  self.assertEqual(ui.session_state['auth04_pending'],'op');count=self.ns['call'].call_count
  with self.assertRaises(PermissionError):self.ns['write_once'](ui,'save_crf',self.step['payload'])
  self.assertEqual(self.ns['call'].call_count,count)
 def test_uncertain_prepare_halts(self):
  ui=UI();self.ns.update(context=Mock(),call=Mock(side_effect=TimeoutError()))
  with self.assertRaises(TimeoutError):self.ns['write_once'](ui,'save_crf',self.step['payload'])
  self.assertTrue(ui.session_state['auth04_preparation_uncertain'])
 def test_nested_read_shape_and_wrong_case_refusal(self):
  p=self.step['payload'];self.ns['call']=Mock(return_value={'ok':True,'result':{'records':[]}})
  self.assertEqual(self.ns['b971_history'](UI(),p),[])
  self.ns['call'].return_value={'ok':True,'result':{'records':[{'record_key':p['record_key'],'payload':{'registration_id':'JUOG-970'}}]}}
  with self.assertRaises(PermissionError):self.ns['b971_history'](UI(),p)
 def test_rejection_must_preserve_history(self):
  self.ns['b971_history']=Mock(return_value=[{'changed':True}])
  with self.assertRaises(PermissionError):self.ns['b971_finish'](UI(),self.step,{'ok':False,'state':'FAILED','error':'VALIDATION_FAILED'},[])
 def test_wrong_rejection_code_never_passes(self):
  self.ns['b971_history']=Mock(return_value=[])
  with self.assertRaises(PermissionError):self.ns['b971_finish'](UI(),self.step,{'ok':False,'state':'FAILED','error':'ACL_DENIED'},[])
 def test_terminal_expected_failed_status_is_reconciled(self):
  state={'auth04_pending':'op','b971_active_step':self.step,'b971_before':[],'auth04_operation_ids':['op'],'b971_halted':True}
  self.ns['b971_history']=Mock(return_value=[])
  ui=self.ui_run(state,'同じoperationの状態照会',Mock(return_value={'ok':True,'state':'FAILED','error':'VALIDATION_FAILED','action':'save_crf'}))
  self.assertIsNone(ui.session_state['auth04_pending']);self.assertEqual(ui.session_state['b971_step'],1)
 def test_recovery_timeout_clears_cached_status_before_execute(self):
  state={'auth04_pending':'op','auth04_operation_ids':['op'],'b971_pending_status_op':'op','b971_pending_status':{'ok':True,'state':'UNFINISHED','phase':'AUDIT_OR_COMMIT_PENDING'}}
  call=Mock(side_effect=TimeoutError());ui=self.ui_run(state,'確認済み同一operationを一度だけ復旧',call)
  self.assertNotIn('b971_pending_status',ui.session_state);self.assertNotIn('b971_pending_status_op',ui.session_state);self.assertEqual(call.call_count,1)
  call=Mock();self.ui_run(ui.session_state,'確認済み同一operationを一度だけ復旧',call);call.assert_not_called()
 def test_stale_status_other_operation_cannot_recover(self):
  state={'auth04_pending':'new','b971_pending_status_op':'old','b971_pending_status':{'ok':True,'state':'UNFINISHED','phase':'AUDIT_OR_COMMIT_PENDING'}}
  call=Mock();self.ui_run(state,'確認済み同一operationを一度だけ復旧',call);call.assert_not_called()
 def test_failed_status_query_drops_cached_permission(self):
  state={'auth04_pending':'op','b971_pending_status_op':'op','b971_pending_status':{'ok':True,'state':'UNFINISHED','phase':'AUDIT_OR_COMMIT_PENDING'}}
  ui=self.ui_run(state,'同じoperationの状態照会',Mock(side_effect=TimeoutError()));self.assertNotIn('b971_pending_status',ui.session_state)
 def test_arbitrary_result_body_and_error_not_rendered(self):
  result=self.ns['summarize']({'ok':False,'state':'secret-state','error':'secret-error','result':{'subject':'secret-subject'},'identity_assertion':'secret-signature'})
  self.assertEqual(result,{'ok':False,'state':None,'error':'UNCLASSIFIED'})
if __name__=='__main__':unittest.main(verbosity=2)

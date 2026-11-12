import sys,types,unittest,copy
from unittest.mock import patch
sys.modules.setdefault('streamlit',types.SimpleNamespace(fragment=lambda **kw:lambda f:f))
import uat_auth04_live as h
class Tests(unittest.TestCase):
 def ui(self):return types.SimpleNamespace(session_state={})
 def test_fixed_case_facility_action_and_actor(self):
  p=h.draft_payload();h.check_payload('save_draft',p)
  for field,value in [('registration_id','JUOG-001'),('facility_code','F01'),('role','admin'),('visit','other')]:
   q=copy.deepcopy(p);q[field]=value
   with self.assertRaises(PermissionError):h.check_payload('save_draft',q)
  with self.assertRaises(PermissionError):h.check_payload('delete_draft',p)
 def test_unknown_operation_never_signed(self):
  ui=self.ui()
  with patch.object(h,'native_context') as native:
   with self.assertRaises(PermissionError):h.call(ui,'execute_request',{'operation_id':'unknown'})
   native.assert_not_called()
 def test_durable_order_and_saved_confirmation(self):
  ui=self.ui();responses=[{'ok':True,'operation_id':'op1'},{'ok':True,'state':'SAVED'},{'ok':True,'state':'SAVED'}]
  with patch.object(h,'context'),patch.object(h,'call',side_effect=responses) as call:
   r=h.write_once(ui,'save_draft',h.draft_payload())
   self.assertEqual([a.args[1] for a in call.call_args_list],['prepare_request','execute_request','request_status'])
   self.assertIsNone(ui.session_state['auth04_pending']);self.assertEqual(r['state'],'SAVED');self.assertEqual(ui.session_state['auth04_last_saved_operation'],'op1')
 def test_uncertain_execute_retains_id_and_blocks_new_prepare(self):
  ui=self.ui()
  with patch.object(h,'context'),patch.object(h,'call',side_effect=[{'ok':True,'operation_id':'op1'},TimeoutError()]):
   with self.assertRaises(TimeoutError):h.write_once(ui,'save_draft',h.draft_payload())
  self.assertEqual(ui.session_state['auth04_pending'],'op1')
  with patch.object(h,'call') as call:
   with self.assertRaises(PermissionError):h.write_once(ui,'save_draft',h.draft_payload())
   call.assert_not_called()
 def test_failed_prepare_does_not_execute(self):
  ui=self.ui()
  with patch.object(h,'context'),patch.object(h,'call',return_value={'ok':False,'error':'DIRECT_IDENTIFIER_NOT_ALLOWED'}) as call:
   self.assertFalse(h.write_once(ui,'save_draft',h.draft_payload())['ok']);self.assertEqual(call.call_count,1)
 def test_uncertain_prepare_cannot_claim_success(self):
  ui=self.ui()
  with patch.object(h,'context'),patch.object(h,'call',side_effect=TimeoutError):
   with self.assertRaises(TimeoutError):h.write_once(ui,'save_draft',h.draft_payload())
  self.assertTrue(ui.session_state['auth04_preparation_uncertain'])
 def test_missing_saved_status_fails(self):
  ui=self.ui()
  with patch.object(h,'context'),patch.object(h,'call',side_effect=[{'ok':True,'operation_id':'op1'},{'ok':True,'state':'SAVED'},{'ok':True,'state':'UNFINISHED'}]):
   with self.assertRaises(PermissionError):h.write_once(ui,'save_draft',h.draft_payload())
 def test_safe_summary_drops_raw_data(self):
  r=h.summarize({'ok':False,'error':'secret arbitrary text','message':'secret','result':{'patient_name':'fictional'}})
  self.assertEqual(r,{'ok':False,'state':None,'error':'UNCLASSIFIED'})
 def test_fixture_payloads_pinned(self):
  for i in range(3):h.check_payload('save_crf',h.crf_payload(i))
  self.assertEqual(h.crf_payload(0,2)['expected_record_version'],1)
 def test_empty_config_fails_before_identity(self):
  ui=self.ui();ui.secrets={'auth04':{},'auth_connect':{}}
  with patch.object(h,'identity_proposal') as auth:
   with self.assertRaises(PermissionError):h.native_context(ui)
   auth.assert_not_called()
 def test_parsed_preparation_unknown_retains_stop(self):
  ui=self.ui()
  with patch.object(h,'context'),patch.object(h,'call',return_value={'ok':False,'state':'UNKNOWN','error':'PREPARATION_UNCERTAIN'}):
   with self.assertRaises(PermissionError):h.write_once(ui,'save_draft',h.draft_payload())
  self.assertTrue(ui.session_state['auth04_preparation_uncertain'])
  with patch.object(h,'call') as call:
   with self.assertRaises(PermissionError):h.write_once(ui,'save_draft',h.draft_payload())
   call.assert_not_called()
 def test_minimal_server_payload_shapes(self):
  ui=self.ui()
  with patch.object(h,'native_context',return_value=object()),patch.object(h,'signed_request',side_effect=lambda n,a,p:p),patch.object(h,'send',side_effect=lambda x:x):
   c=h.call(ui,'ui_context',{'registration_id':h.CASE,'facility_code':h.FACILITY})
   self.assertEqual(set(c['payload']),{'registration_id'})
   r=h.call(ui,'read_crf',h.read_payload())
   self.assertEqual(set(r['payload']),{'registration_id','facility_code','record_key'})
 def test_linkage_uses_actual_latest30d(self):
  ui=self.ui();latest={'record_version':2,'submission_id':'actual-version-two'}
  with patch.object(h,'read_records',return_value=({},[latest])):
   p=h.linked_crf_payload(ui,1)
  self.assertEqual(p['data']['source_30d_record_version'],2);self.assertEqual(p['data']['source_30d_submission_id'],'actual-version-two')
 def test_history_detects_mutated_old_record(self):
  ui=self.ui();p=h.crf_payload(0);ui.session_state={'auth04_expected_versions':{0:1},'auth04_expected_payloads':{'0:1':p}}
  record={'record_key':p['record_key'],'record_version':1,'payload':p,'accepted_at':'fixed'}
  with patch.object(h,'read_records',return_value=({'ok':True},[record])):h.verify_history(ui,0)
  changed=copy.deepcopy(record);changed['accepted_at']='changed'
  with patch.object(h,'read_records',return_value=({'ok':True},[changed])):
   with self.assertRaises(PermissionError):h.verify_history(ui,0)
 def test_normal_write_rejection_is_failure(self):
  ui=self.ui()
  with patch.object(h,'write_once',return_value={'ok':False,'error':'ACL_DENIED'}):
   with self.assertRaises(PermissionError):h.save_expected_crf(ui,0,1)

 def test_expired_and_loggedout_controls_do_not_send(self):
  class Stop(BaseException):pass
  class User(dict):is_logged_in=True
  class Fake:
   session_state={}
   def __getattr__(self,n):return lambda *a,**k:None
   def button(self,n):return True
   def stop(self):raise Stop()
   def login(self,method):self.logged_in_method=method
   def logout(self):self.logged_out=True
  ui=Fake();ui.user=User(iat=1,exp=2)
  with patch.object(h,'st',ui),patch.object(h,'native_context',side_effect=PermissionError),patch.object(h,'send') as send:
   with self.assertRaises(Stop):h.run()
   self.assertTrue(ui.logged_out);send.assert_not_called()
  ui=Fake();ui.user=User(iat=int(h.time.time()),exp=int(h.time.time())+3600);ui.logged_out=False
  with patch.object(h,'st',ui),patch.object(h,'native_context',side_effect=PermissionError),patch.object(h,'send') as send:
   with self.assertRaises(Stop):h.run()
   self.assertFalse(ui.logged_out);send.assert_not_called()
  ui=Fake();ui.user=User();ui.user.is_logged_in=False
  with patch.object(h,'st',ui),patch.object(h,'native_context') as native,patch.object(h,'send') as send:
   with self.assertRaises(Stop):h.run()
   self.assertEqual(ui.logged_in_method,'google');native.assert_not_called();send.assert_not_called()

 def test_legacy_server_redaction_cannot_be_masked_by_local_scrub(self):
  ui=self.ui();bad=h.expected_legacy90d();bad['d90_patient_name']={'value':'SYNTHETIC-ID'}
  with patch.object(h,'call',return_value={'ok':True,'result':{'source_found':True,'draft_state':bad}}),patch.object(h,'restore_draft_state') as restore:
   with self.assertRaises(PermissionError):h.legacy90d_read_restore(ui)
   restore.assert_not_called()
 def test_legacy_server_read_then_clear_restore(self):
  ui=self.ui();expected=h.expected_legacy90d()
  def clear(prefixes):ui.session_state.clear()
  def restore(draft):ui.session_state.update(copy.deepcopy(draft))
  with patch.object(h,'call',return_value={'ok':True,'result':{'source_found':True,'draft_state':expected}}),patch.object(h,'clear_session_state_prefixes',side_effect=clear),patch.object(h,'restore_draft_state',side_effect=restore),patch.object(h,'capture_draft_state',side_effect=lambda prefix:ui.session_state.copy()):
   self.assertTrue(h.legacy90d_read_restore(ui)['ok'])
  self.assertNotIn('d90_patient_name',ui.session_state)
 def test_owner_rejection_requires_exact_reason(self):
  ui=self.ui()
  with patch.object(h,'call',return_value={'ok':False,'error':'DRAFT_OWNER_REQUIRED'}):self.assertFalse(h.other_owner_read_denied(ui)['ok'])
  for result in ({'ok':True},{'ok':False,'error':'ACL_DENIED'},{'ok':False,'error':'UNIFIED_TRANSACTION_INCOMPLETE'}):
   with patch.object(h,'call',return_value=result):
    with self.assertRaises(PermissionError):h.other_owner_read_denied(ui)

if __name__=='__main__':unittest.main()

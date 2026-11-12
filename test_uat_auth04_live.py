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
 def test_privacy_one_request_per_click_and_completion_no_resend(self):
  ui=self.ui();rejection={'ok':False,'error':'DIRECT_IDENTIFIER_NOT_ALLOWED'}
  with patch.object(h,'call',return_value=rejection) as call:
   for i in range(16):
    self.assertEqual(h.privacy_probe_once(ui),rejection)
    self.assertEqual(call.call_count,i+1)
    self.assertEqual(ui.session_state['auth04_privacy_next'],i+1)
    self.assertEqual(call.call_args.args[2]['payload']['draft_state']['privacy_probe'],h.PRIVACY_FIXTURES[i])
   with self.assertRaises(PermissionError):h.privacy_probe_once(ui)
   self.assertEqual(call.call_count,16)
  self.assertEqual([r['fixture'] for r in ui.session_state['auth04_privacy_progress']],list(range(1,17)))
  self.assertTrue(all(r['confirmed'] for r in ui.session_state['auth04_privacy_progress']))
 def test_privacy_timeout_retains_uncertain_blocks_retry_and_hides_message(self):
  ui=self.ui()
  with patch.object(h,'call',side_effect=TimeoutError('DO_NOT_DISPLAY_secret_url')) as call:
   with self.assertRaises(TimeoutError):h.privacy_probe_once(ui)
   with self.assertRaises(PermissionError):h.privacy_probe_once(ui)
   call.assert_called_once()
  self.assertTrue(ui.session_state['auth04_preparation_uncertain']);self.assertTrue(ui.session_state['auth04_halted'])
  progress=ui.session_state['auth04_privacy_progress']
  self.assertEqual(progress,[{'fixture':1,'confirmed':False,'category':'TIMEOUT','elapsed':'LT_15S'}])
 def test_privacy_response_allowlist_and_pending_id_remain_private(self):
  for result in ({'ok':False,'error':'AUTH_EXPIRED'}, {'ok':False,'error':'DO_NOT_DISPLAY_secret'}, {'ok':True,'operation_id':'PRIVATE_OPERATION_ID','data':'secret'}):
   ui=self.ui()
   with patch.object(h,'call',return_value=result) as call:
    with self.assertRaises(PermissionError):h.privacy_probe_once(ui)
    with self.assertRaises(PermissionError):h.privacy_probe_once(ui)
    call.assert_called_once()
   text=str(ui.session_state['auth04_privacy_progress'])
   self.assertNotIn('DO_NOT_DISPLAY',text);self.assertNotIn('PRIVATE_OPERATION_ID',text);self.assertNotIn('secret',text)
   if result.get('operation_id'):self.assertEqual(ui.session_state['auth04_pending'],'PRIVATE_OPERATION_ID')
   self.assertNotIn('auth04_privacy_next',ui.session_state)
 def test_privacy_local_window_closure_is_not_sent_or_uncertain(self):
  ui=self.ui()
  with patch.object(h,'call',side_effect=h.PrepareWindowClosed('unused')):
   with self.assertRaises(h.PrepareWindowClosed):h.privacy_probe_once(ui)
  self.assertFalse(ui.session_state['auth04_preparation_uncertain'])
  self.assertEqual(ui.session_state['auth04_privacy_progress'][0]['category'],'LOCAL_WINDOW_CLOSED')
  self.assertNotIn('auth04_privacy_next',ui.session_state)
 def test_safe_exception_categories_never_format_exception(self):
  class Hostile(Exception):
   def __str__(self):raise AssertionError('Must not format')
  cases=[(Hostile(),'LOCAL_CHECK_FAILED'),(TimeoutError('secret'),'TIMEOUT'),(h.urllib.error.URLError(TimeoutError('secret')),'TIMEOUT'),(h.urllib.error.URLError('secret-url'),'TRANSPORT_ERROR'),(h.urllib.error.HTTPError('secret-url',500,'secret',{},None),'HTTP_ERROR'),(h.json.JSONDecodeError('secret','secret',0),'INVALID_JSON')]
  for exc,expected in cases:self.assertEqual(h.safe_exception_category(exc),expected)
 def test_diagnostic_latency_boundaries(self):
  for now,expected in [(14.999,'LT_15S'),(15,'15_TO_30S'),(29.999,'15_TO_30S'),(30,'GE_30S')]:
   with patch.object(h.time,'monotonic',return_value=now):self.assertEqual(h.elapsed_bucket(0),expected)
 def test_persistent_progress_renders_before_halt_without_new_request(self):
  class Stop(BaseException):pass
  class Fake:
   user=types.SimpleNamespace(is_logged_in=True)
   session_state={'auth04_halted':True,'auth04_privacy_progress':[{'fixture':2,'confirmed':False,'category':'TIMEOUT'}],'auth04_results':[{'check':'接続・対象症例確認','ok':True}]}
   shown=[]
   def __getattr__(self,n):return lambda *a,**k:None
   def table(self,rows):self.shown.append(rows)
   def stop(self):raise Stop()
  ui=Fake()
  with patch.object(h,'st',ui),patch.object(h,'native_context'),patch.object(h,'send') as send:
   with self.assertRaises(Stop):h.run()
   send.assert_not_called()
  self.assertIn(ui.session_state['auth04_privacy_progress'],ui.shown);self.assertIn(ui.session_state['auth04_results'],ui.shown)
 def recovery_ui_and_payload(self):
  ui=self.ui();ui.session_state={'auth04_pending':'observed90','auth04_operation_ids':['observed90'],'auth04_expected_versions':{0:2},'auth04_halted':True}
  p=h.crf_payload(1);p['data']['source_30d_record_version']=2;p['data']['source_30d_submission_id']='synthetic30v2'
  return ui,p
 def test_recovery_only_same_observed_id_no_prepare_and_exact_read(self):
  ui,p=self.recovery_ui_and_payload();rec={'record_key':p['record_key'],'record_version':1,'payload':p,'accepted_at':'synthetic'}
  responses=[{'ok':True,'action':'save_crf','state':'UNFINISHED','phase':'AUDIT_OR_COMMIT_PENDING'},{'ok':True,'state':'SAVED'},{'ok':True,'action':'save_crf','state':'SAVED'}]
  with patch.object(h,'linked_crf_payload',return_value=p),patch.object(h,'call',side_effect=responses) as call,patch.object(h,'read_records',return_value=({'ok':True},[rec])):
   self.assertEqual(h.resume_observed_90d(ui)['state'],'SAVED')
   self.assertEqual([c.args[1] for c in call.call_args_list],['request_status','execute_request','request_status'])
   self.assertTrue(all(c.args[2]=={'operation_id':'observed90'} for c in call.call_args_list))
  self.assertIsNone(ui.session_state['auth04_pending']);self.assertFalse(ui.session_state['auth04_halted'])
  self.assertEqual(ui.session_state['auth04_expected_versions'][1],1)
 def test_recovery_unknown_or_prepared_without_intent_never_executes(self):
  for status in ({'ok':True,'action':'save_crf','state':'UNKNOWN'}, {'ok':True,'action':'save_crf','state':'UNFINISHED','phase':'PREPARED'},{'ok':True,'action':'save_draft','state':'UNFINISHED','phase':'AUDIT_OR_COMMIT_PENDING'}):
   ui,p=self.recovery_ui_and_payload()
   with patch.object(h,'linked_crf_payload',return_value=p),patch.object(h,'call',return_value=status) as call:
    with self.assertRaises(PermissionError):h.resume_observed_90d(ui)
    call.assert_called_once()
   self.assertEqual(ui.session_state['auth04_pending'],'observed90');self.assertTrue(ui.session_state['auth04_halted'])
 def test_recovery_wrong_record_keeps_halt_and_pending(self):
  for change in ('payload','version','extra_record'):
   ui,p=self.recovery_ui_and_payload();rec={'record_key':p['record_key'],'record_version':1,'payload':copy.deepcopy(p)}
   if change=='payload':rec['payload']['data']['source_30d_record_version']=1
   if change=='version':rec['record_version']=2
   records=[rec,copy.deepcopy(rec)] if change=='extra_record' else [rec]
   with patch.object(h,'linked_crf_payload',return_value=p),patch.object(h,'call',return_value={'ok':True,'action':'save_crf','state':'SAVED'}),patch.object(h,'read_records',return_value=({'ok':True},records)):
    with self.assertRaises(PermissionError):h.resume_observed_90d(ui)
   self.assertEqual(ui.session_state['auth04_pending'],'observed90');self.assertTrue(ui.session_state['auth04_halted']);self.assertNotIn(1,ui.session_state['auth04_expected_versions'])
 def test_recovery_timeout_no_automatic_retry(self):
  ui,p=self.recovery_ui_and_payload()
  with patch.object(h,'linked_crf_payload',return_value=p),patch.object(h,'call',side_effect=[{'ok':True,'action':'save_crf','state':'UNFINISHED','phase':'AUDIT_OR_COMMIT_PENDING'},TimeoutError('hidden')]) as call:
   with self.assertRaises(TimeoutError):h.resume_observed_90d(ui)
   self.assertEqual(call.call_count,2)
  self.assertEqual(ui.session_state['auth04_pending'],'observed90');self.assertTrue(ui.session_state['auth04_halted'])
 def test_recovery_failed_readback_rolls_back_expectations(self):
  ui,p=self.recovery_ui_and_payload();rec={'record_key':p['record_key'],'record_version':1,'payload':p}
  with patch.object(h,'linked_crf_payload',return_value=p),patch.object(h,'call',return_value={'ok':True,'action':'save_crf','state':'SAVED'}),patch.object(h,'read_records',return_value=({'ok':True},[rec])),patch.object(h,'verify_history',side_effect=PermissionError):
   with self.assertRaises(PermissionError):h.resume_observed_90d(ui)
  self.assertEqual(ui.session_state['auth04_expected_versions'],{0:2});self.assertTrue(ui.session_state['auth04_halted']);self.assertEqual(ui.session_state['auth04_pending'],'observed90')
 def test_execution_diagnostic_retains_safe_failure_before_status(self):
  ui=self.ui()
  with patch.object(h,'context'),patch.object(h,'call',side_effect=[{'ok':True,'operation_id':'secret_op'},{'ok':False,'error':'DOMAIN_INCOMPLETE','state':'UNFINISHED','raw':'secret'},TimeoutError]):
   with self.assertRaises(TimeoutError):h.write_once(ui,'save_crf',h.crf_payload(1))
  self.assertEqual(ui.session_state['auth04_execution_diagnostics'],[{'phase':'EXECUTE','ok':False,'state':'UNFINISHED','error':'DOMAIN_INCOMPLETE'}])
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

 def test_prepare_margin_exact_boundary_and_shorter_expiry(self):
  ui=self.ui();body={'action':'save_draft','payload':h.draft_payload()}
  for iat,exp,allowed in [(1000,6000,True),(999,6000,False),(1000,4599,False),(True,6000,False)]:
   native=types.SimpleNamespace(user={'iat':iat,'exp':exp})
   with self.subTest(iat=iat,exp=exp),patch.object(h,'native_context',return_value=native),patch.object(h.time,'time',return_value=3700),patch.object(h,'signed_request',return_value={}) as signed,patch.object(h,'send',return_value={'ok':True}) as send:
    if allowed:self.assertTrue(h.call(ui,'prepare_request',body)['ok']);send.assert_called_once()
    else:
     with self.assertRaises(h.PrepareWindowClosed):h.call(ui,'prepare_request',body)
     signed.assert_not_called();send.assert_not_called()
 def test_prepare_margin_rechecked_after_signing(self):
  ui=self.ui();native=types.SimpleNamespace(user={'iat':1000,'exp':6000})
  with patch.object(h,'native_context',return_value=native),patch.object(h.time,'time',side_effect=[3700,3701]),patch.object(h,'signed_request',return_value={}),patch.object(h,'send') as send:
   with self.assertRaises(h.PrepareWindowClosed):h.call(ui,'prepare_request',{'action':'save_draft','payload':h.draft_payload()})
   send.assert_not_called()
 def test_margin_does_not_block_observed_reconciliation_or_reads(self):
  ui=self.ui();ui.session_state['auth04_operation_ids']=['observed']
  native=types.SimpleNamespace(user={'iat':1000,'exp':6000})
  with patch.object(h,'native_context',return_value=native),patch.object(h.time,'time',return_value=4599),patch.object(h,'signed_request',return_value={}),patch.object(h,'send',return_value={'ok':True}) as send:
   for action in ('request_status','execute_request'):self.assertTrue(h.call(ui,action,{'operation_id':'observed'})['ok'])
   self.assertTrue(h.call(ui,'read_crf',h.read_payload())['ok']);self.assertEqual(send.call_count,3)
 def test_local_margin_refusal_is_not_uncertain_prepare(self):
  ui=self.ui()
  with patch.object(h,'context'),patch.object(h,'call',side_effect=h.PrepareWindowClosed('AUTH04_PREPARE_WINDOW_CLOSED')):
   with self.assertRaises(h.PrepareWindowClosed):h.write_once(ui,'save_draft',h.draft_payload())
  self.assertFalse(ui.session_state['auth04_preparation_uncertain']);self.assertNotIn('auth04_pending',ui.session_state)
 def test_legacy_representation_drift_rejected_before_restore(self):
  variants=[]
  for key,value in [('d90_nested',{'CRP':0}),('d90_age',46.0),('d90_age',True)]:
   bad=h.expected_legacy90d();bad[key]['value']=value;variants.append(bad)
  bad=h.expected_legacy90d();bad['d90_nested']={'type':'value','value':'{"CRP":0}','extra':'unexpected'};variants.append(bad)
  variants.append(__import__('json').dumps(h.expected_legacy90d()))
  for bad in variants:
   with self.subTest(draft_type=type(bad).__name__),patch.object(h,'call',return_value={'ok':True,'result':{'source_found':True,'draft_state':bad}}),patch.object(h,'restore_draft_state') as restore:
    with self.assertRaises(PermissionError):h.legacy90d_read_restore(self.ui())
    restore.assert_not_called()
  expected=h.expected_legacy90d();equivalent=copy.deepcopy(expected);equivalent['d90_nested']['value']='{ "CRP" : 0 }'
  self.assertTrue(h.legacy90d_matches(equivalent,expected))

if __name__=='__main__':unittest.main()

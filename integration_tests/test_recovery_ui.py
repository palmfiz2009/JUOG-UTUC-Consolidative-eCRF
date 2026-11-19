import unittest
from unittest.mock import patch
import isolated_recovery_ui as recovery
class UI:
 def __init__(self,clicked=()):self.session_state={'_recovery_open':True};self.clicked=clicked;self.messages=[]
 def text_input(self,*a,**k):return 'JUOG-901'
 def selectbox(self,*a,**k):return '30日'
 def button(self,*a,**k):return k['key'] in self.clicked
 def __getattr__(self,name):return lambda message:self.messages.append((name,message))
def response(state,ops=None):return {'ok':True,'recovery':{'state':state,'operations':ops or []}}
class RecoveryUI(unittest.TestCase):
 def test_unknown_and_transport_failure_block_new(self):
  for reply in ({'ok':False},response('NO_SERVER_RECORD'),response('NEEDS_RECONCILIATION')):
   ui=UI()
   with patch.object(recovery,'call',return_value=reply) as call:recovery.render(ui)
   self.assertTrue(ui.session_state['_recovery_blocks_new']);self.assertEqual(call.call_count,1)
   self.assertFalse(any(kind=='success' for kind,_ in ui.messages))
 def test_retry_sends_only_server_uuid_then_rechecks(self):
  ui=UI(['_recover_original']);op={'state':'RETRY_ALLOWED','uuid':'original'}
  saved={'state':'SAVED','uuid':'original','version':1,'audit_verified':True}
  with patch.object(recovery,'call',side_effect=[response('RETRY_ALLOWED',[op]),{'ok':True},response('SAVED',[saved])]) as call:recovery.render(ui)
  sent=call.call_args_list[1].args
  self.assertEqual(sent[1],'recovery_retry');self.assertEqual(set(sent[2]),{'registration_id','facility_code','crf_type','visit','submission_id'})
  self.assertEqual(sent[2]['submission_id'],'original');self.assertEqual(call.call_count,3)
  self.assertTrue(any(k=='success' for k,_ in ui.messages))
 def test_unverified_retry_never_shows_success(self):
  for reply in ({'ok':False},response('NO_SERVER_RECORD')):
   ui=UI(['_recover_original'])
   with patch.object(recovery,'call',side_effect=[response('RETRY_ALLOWED',[{'state':'RETRY_ALLOWED','uuid':'original'}]),{'ok':True},reply]):recovery.render(ui)
   self.assertTrue(ui.session_state['_recovery_blocks_new']);self.assertFalse(any(k=='success' for k,_ in ui.messages))
 def test_saved_marks_only_matching_attempt_complete(self):
  ui=UI();ui.session_state['_juog_peri_save_attempt']={'payload':{'submission_id':'original'},'status':'uncertain'};ui.session_state['_juog_d90_save_attempt']={'payload':{'submission_id':'other'},'status':'uncertain'}
  with patch.object(recovery,'call',return_value=response('SAVED',[{'state':'SAVED','uuid':'original','version':1,'audit_verified':True}])):recovery.render(ui)
  self.assertEqual(ui.session_state['_juog_peri_save_attempt']['status'],'complete');self.assertEqual(ui.session_state['_juog_d90_save_attempt']['status'],'uncertain')

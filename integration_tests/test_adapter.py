"""Native claims are synthetic. Exercise the real signer; transport is intercepted."""
import base64,copy,hashlib,hmac,json,time,unittest
from types import SimpleNamespace
from unittest.mock import patch
import isolated_crf_adapter as a

class User(dict):is_logged_in=True
class Tests(unittest.TestCase):
 def setUp(self):
  self.now=int(time.time())
  self.user=User(iss='https://accounts.google.com',sub='fictional-sub',aud='offline-client',nonce='fictional-nonce',iat=self.now,exp=self.now+7200)
  self.profile=dict(enabled=True,stage=a.STAGE,script_id=a.SCRIPT,spreadsheet_id=a.SHEET,url='https://script.google.com/macros/s/OFFLINE-NOT-AN-ENDPOINT/exec',generation='OFFLINE_ONLY',principal_fingerprint=a.identity_proposal(self.user,'offline-client',self.now)['principal_fingerprint'],qa_ref='OFFLINE_NOT_APPROVAL',pi_ref='OFFLINE_NOT_APPROVAL',single_writer_ref='OFFLINE_NOT_APPROVAL',backup_ref='OFFLINE_NOT_APPROVAL',b2_policy_ref='OFFLINE_NOT_APPROVAL')
  self.ui=SimpleNamespace(user=self.user,session_state={},secrets={'auth':{'google':{'client_id':'offline-client'}},'isolated_crf':{k:self.profile[k] for k in ('url','generation','script_id','spreadsheet_id')},'registry':{'expected_spreadsheet_id':a.SHEET}})
  self.ui.secrets['isolated_crf']['signing_key']='OFFLINE-KEY-NOT-A-CREDENTIAL-00000000'
  self.payload={'registration_id':'JUOG-901','facility_code':'TEST01','crf_type':'perioperative_30d','visit':'30d','record_key':'JUOG-901|perioperative_30d|30d','submission_id':'offline-uuid','data':{'zero':0,'flag':False}}
  self.ui.session_state['_integration_edit_subject']='JUOG-901'
  self.payload['reporter_email']='fictional@example.invalid'
  self.sent=[]
  self.profile_patch=patch.object(a,'load_profile',return_value=self.profile);self.profile_patch.start();self.addCleanup(self.profile_patch.stop)
  self.tx=patch.object(a,'transport',side_effect=self.send).start();self.addCleanup(patch.stopall)
 def send(self,url,envelope,timeout):
  encoded,signature=envelope['identity_assertion'].split('.')
  expected=base64.urlsafe_b64encode(hmac.new(self.ui.secrets['isolated_crf']['signing_key'].encode(),encoded.encode(),hashlib.sha256).digest()).decode().rstrip('=')
  self.assertTrue(hmac.compare_digest(expected,signature))
  claims=json.loads(base64.urlsafe_b64decode(encoded+'='*(-len(encoded)%4)))
  self.assertEqual(claims['request_hash'],hashlib.sha256(envelope['request_json'].encode()).hexdigest())
  self.assertEqual(claims['v'],2);self.assertLessEqual(claims['exp']-claims['iat'],15)
  req=json.loads(envelope['request_json']);self.sent.append((req,claims))
  r=dict(ok=True,spreadsheet_id=a.SHEET,script_id=a.SCRIPT,integration_stage=a.STAGE,generation=self.profile['generation'],role='facility',facility_code='TEST01')
  if req['action']=='validate':r['record_versions']={self.payload['record_key']:1}
  return r
 def test_disabled_and_missing_approvals_never_send(self):
  for k in ('enabled','qa_ref','pi_ref','backup_ref','single_writer_ref','b2_policy_ref'):
   old=self.profile[k];self.profile[k]=False if k=='enabled' else ''
   self.assertFalse(a.call(self.ui,'ui_context')['ok']);self.profile[k]=old
  self.tx.assert_not_called()
 def test_config_and_native_identity_denials_no_transport(self):
  for key,value in [('aud','wrong'),('iss','wrong'),('exp',self.now-1),('iat',self.now-3600),('nonce',''),('sub','other')]:
   old=self.user[key];self.user[key]=value
   self.assertFalse(a.call(self.ui,'ui_context')['ok']);self.user[key]=old
  self.user.is_logged_in=False;self.assertFalse(a.call(self.ui,'ui_context')['ok']);self.tx.assert_not_called()
 def test_validate_observes_version_frozen_retry_new_jti(self):
  self.assertTrue(a.call(self.ui,'validate',{'registration_id':'JUOG-901'})['ok'])
  self.assertTrue(a.call(self.ui,'save_crf',{'payload':self.payload})['ok'])
  self.ui.session_state['_integration_versions'][self.payload['record_key']]=8
  self.assertTrue(a.call(self.ui,'save_crf',{'payload':self.payload})['ok'])
  req1,c1=self.sent[-2];req2,c2=self.sent[-1]
  self.assertEqual(req1,req2);self.assertEqual(req1['payload']['expected_record_version'],1)
  self.assertNotEqual(c1['session']['jti'],c2['session']['jti']);self.assertEqual(c1['session']['sid'],c2['session']['sid'])
 def test_no_observed_version_or_uuid_content_conflict(self):
  self.assertEqual(a.call(self.ui,'save_crf',{'payload':self.payload})['error'],'OBSERVED_VERSION_REQUIRED');self.tx.assert_not_called()
  a.call(self.ui,'validate',{'registration_id':'JUOG-901'});a.call(self.ui,'save_crf',{'payload':self.payload})
  self.payload['data']['zero']=1
  self.assertEqual(a.call(self.ui,'save_crf',{'payload':self.payload})['error'],'SUBMISSION_ID_CONFLICT')
  self.assertEqual(self.tx.call_count,2)
 def test_transport_loss_not_retried_or_exposed(self):
  self.tx.side_effect=TimeoutError('SENSITIVE_URL_OR_TOKEN')
  r=a.call(self.ui,'ui_context');self.assertEqual(r,{'ok':False,'error':'RESULT_UNCONFIRMED'});self.assertEqual(self.tx.call_count,1)
 def test_mismatched_receipt_not_accepted(self):
  self.tx.return_value={};self.tx.side_effect=lambda *a,**k:{'ok':True,'spreadsheet_id':'other'}
  self.assertEqual(a.call(self.ui,'ui_context')['error'],'RESPONSE_BINDING_MISMATCH')
 def test_acl_revocation_latches_halt(self):
  self.tx.side_effect=lambda *a,**k:{'ok':False,'error':'SESSION_REVOKED'}
  a.call(self.ui,'ui_context');self.assertTrue(self.ui.session_state['auth_connect_halted'])
  a.call(self.ui,'ui_context');self.assertEqual(self.tx.call_count,1)
 def test_actor_change_does_not_inherit_pending(self):
  a.call(self.ui,'validate',{'registration_id':'JUOG-901'})
  self.user['sub']='second-fictional';self.profile['principal_fingerprint']=a.identity_proposal(self.user,'offline-client',self.now)['principal_fingerprint']
  self.assertEqual(a.call(self.ui,'save_crf',{'payload':self.payload})['error'],'ACTOR_CHANGED');self.assertEqual(self.tx.call_count,1)
 def test_unsupported_route_has_no_token_fallback(self):
  self.assertEqual(a.call(self.ui,'register',{})['error'],'ROUTE_DENIED');self.tx.assert_not_called()
 def test_fresh_auth_time_policy_is_not_silently_disabled(self):
  from uat_b2_auth_bridge import signed_request
  native,_=a.context(self.ui);cfg=native.secrets['juog_identity_bridge'];cfg.update(session_policy='google_auth_time',max_auth_age_seconds=3600)
  with self.assertRaises(PermissionError):signed_request(native,'ui_context',{})
 def test_logout_still_requires_config_and_signed_request(self):
  self.ui.session_state['auth_connect_halted']=True
  a.call(self.ui,'session_revoke',{});self.assertEqual(self.sent[0][0],{'action':'session_revoke','payload':{}})
 def test_submission_validate_cannot_silently_advance_observed_version(self):
  key=self.payload['record_key'];self.ui.session_state['_integration_versions']={key:0}
  a.call(self.ui,'validate',{'registration_id':'JUOG-901'})
  self.assertEqual(self.ui.session_state['_integration_versions'][key],0)
  self.assertTrue(a.begin_edit(self.ui,'JUOG-901')['ok'])
  self.assertEqual(self.ui.session_state['_integration_versions'][key],1)
 def test_begin_edit_blocks_unresolved_helper_attempt(self):
  self.ui.session_state['_juog_peri_save_attempt']={'status':'uncertain'}
  self.assertEqual(a.begin_edit(self.ui,'JUOG-901')['error'],'RECONCILE_PENDING_FIRST');self.tx.assert_not_called()
 def test_fixture_privacy_not_weakened(self):
  for data in [{'regBirthDate':'1980-01-02'},{'text':'生年月日1980年1月2日'},{'nested':'{"ＭＲＮ":"FICTIONAL"}'}]:
   self.payload['data']=data
   self.assertEqual(a.call(self.ui,'save_crf',{'payload':self.payload})['error'],'DIRECT_IDENTIFIER_NOT_ALLOWED')
  self.tx.assert_not_called()

 def test_expired_read_retries_once_with_new_signature(self):
  def send(url,envelope,timeout):
   r=self.send(url,envelope,timeout)
   return {'ok':False,'error':'AUTH_EXPIRED'} if len(self.sent)==1 else r
  self.tx.side_effect=send
  self.assertTrue(a.call(self.ui,'ui_context')['ok'])
  self.assertEqual(len(self.sent),2)
  self.assertNotEqual(self.sent[0][1]['session']['jti'],self.sent[1][1]['session']['jti'])
 def test_expired_read_retry_is_bounded(self):
  def send(url,envelope,timeout):
   self.send(url,envelope,timeout)
   return {'ok':False,'error':'AUTH_EXPIRED'}
  self.tx.side_effect=send
  self.assertFalse(a.call(self.ui,'ui_context')['ok'])
  self.assertEqual(len(self.sent),2)
  self.assertTrue(self.ui.session_state['auth_connect_halted'])

 def recovery_transport(self, first_error='AUTH_EXPIRED', alter=None):
  def send(url,envelope,timeout):
   binding=self.send(url,envelope,timeout)
   req=self.sent[-1][0]; action=req['action']; b=self.payload
   if action=='save_crf':
    if first_error=='timeout':raise TimeoutError('not exposed')
    return {'ok':False,'error':first_error}
   if action=='recovery_status':
    op=dict(uuid=b['submission_id'],state='SAVED',version=2,audit_verified=True,digest=hashlib.sha256(json.dumps(b,ensure_ascii=False,separators=(',',':')).encode()).hexdigest())
    if alter:op.update(alter)
    return dict(binding,recovery=dict(record_key=b['record_key'],state='SAVED',operations=[op]))
   if action=='request_status':
    receipt=dict(ok=True,audit_verified=True,record_version=2,existing=False,spreadsheet_id=a.SHEET,**{k:b[k] for k in ('submission_id','record_key','crf_type','visit')})
    return dict(binding,state='COMMITTED_RECHECK_REQUIRED',receipt=receipt)
   return binding
  self.tx.side_effect=send
 def test_expired_save_response_fresh_signed_read_reconciles_without_write_retry(self):
  a.call(self.ui,'validate',{'registration_id':'JUOG-901'});self.sent=[]
  self.recovery_transport()
  r=a.call(self.ui,'save_crf',{'payload':self.payload})
  self.assertTrue(r['ok']);self.assertTrue(r['reconciled_after_uncertain_response'])
  self.assertEqual([x[0]['action'] for x in self.sent],['save_crf','recovery_status','request_status'])
  self.assertEqual(len({x[1]['session']['jti'] for x in self.sent}),3)
  self.assertFalse(self.ui.session_state.get('auth_connect_halted'))
 def test_lost_save_response_reconciles_read_only(self):
  a.call(self.ui,'validate',{'registration_id':'JUOG-901'});self.sent=[]
  self.recovery_transport('timeout')
  self.assertTrue(a.call(self.ui,'save_crf',{'payload':self.payload})['ok'])
  self.assertEqual(sum(x[0]['action']=='save_crf' for x in self.sent),1)
 def test_reconciliation_digest_version_audit_mismatch_never_success(self):
  for alter in ({'digest':'wrong'},{'version':3},{'audit_verified':False},{'uuid':'another'}):
   self.ui.session_state.clear();self.ui.session_state['_integration_edit_subject']='JUOG-901'
   self.ui.session_state['_integration_versions']={self.payload['record_key']:1}
   self.sent=[];self.recovery_transport(alter=alter)
   self.assertFalse(a.call(self.ui,'save_crf',{'payload':self.payload})['ok'])
   self.assertTrue(self.ui.session_state['_recovery_blocks_new'])
   self.assertNotIn('request_status',[x[0]['action'] for x in self.sent])
 def test_revoked_save_never_triggers_reconciliation(self):
  self.ui.session_state['_integration_versions']={self.payload['record_key']:1}
  self.recovery_transport('SESSION_REVOKED')
  self.assertFalse(a.call(self.ui,'save_crf',{'payload':self.payload})['ok'])
  self.assertEqual([x[0]['action'] for x in self.sent],['save_crf'])
  self.assertTrue(self.ui.session_state['auth_connect_halted'])

if __name__=='__main__':unittest.main()

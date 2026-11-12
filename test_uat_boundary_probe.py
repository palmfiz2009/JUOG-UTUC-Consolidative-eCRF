import sys, unittest, base64, json
from types import SimpleNamespace
from unittest.mock import Mock, patch
sys.modules.setdefault('streamlit',SimpleNamespace(fragment=lambda **kw: lambda f:f))
import uat_boundary_probe as b
class User(dict):is_logged_in=True
class Tests(unittest.TestCase):
 def setUp(self):
  self.u=User(iss='synthetic',sub='synthetic',iat=1000,exp=9000,nonce='n')
  self.s=dict(phase='WAITING',started=1000,deadline=4600,duration=3600,token_identity=b.token_identity(self.u))
  self.ctx=Mock(return_value=object());self.make=Mock(side_effect=self.envelope);self.send=Mock(return_value={'ok':True})
 def envelope(self,native):
  claims={'v':2,'iat':int(b.time.time()),'exp':min(int(b.time.time())+15,4600),'session':{'deadline':4600,'token_iat':1000,'sid':'synthetic-session','generation':'synthetic-generation'}}
  return {'identity_assertion':base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip('=')+'.synthetic-signature'}
 def step(self,t):
  with patch.object(b.time,'time',return_value=t):b.advance(self.s,t,self.u,self.ctx,self.make,self.send,lambda r:r.get('ok') is True)
 def test_exact_boundary_same_deadline_envelope_sent_once(self):
  self.step(4580);self.assertEqual(self.s['phase'],'WAITING_EXPIRY')
  self.step(4590);self.assertIn('pending_envelope',self.s)
  self.ctx.side_effect=PermissionError('RELOGIN_REQUIRED');self.send.return_value={'ok':False,'error':'AUTH_EXPIRED'};self.step(4600)
  self.assertEqual(self.s['phase'],'DONE');self.assertEqual(self.send.call_count,2)
  self.assertTrue(self.s['gas_expired_denied']);self.assertNotIn('pending_envelope',self.s)
  self.step(4605);self.assertEqual(self.send.call_count,2)
 def test_missing_pending_does_not_claim_full_pass(self):
  self.step(4580);self.ctx.side_effect=PermissionError('RELOGIN_REQUIRED');self.step(4600)
  self.assertEqual(self.s['phase'],'FAILED');self.assertTrue(self.s['signer_denied']);self.assertEqual(self.send.call_count,1)
 def test_generic_gas_error_is_not_expiry_pass(self):
  self.step(4580);self.step(4595);self.ctx.side_effect=PermissionError('APP_SESSION_EXPIRED')
  self.send.return_value={'ok':False,'error':'UNIFIED_TRANSACTION_INCOMPLETE'};self.step(4600)
  self.assertEqual(self.s['phase'],'FAILED');self.assertNotIn('pending_envelope',self.s)
 def test_pending_send_timeout_never_retries(self):
  self.step(4580);self.step(4595);self.ctx.side_effect=PermissionError('APP_SESSION_EXPIRED')
  self.send.side_effect=TimeoutError();self.step(4600);self.step(4605)
  self.assertEqual(self.s['phase'],'FAILED');self.assertEqual(self.send.call_count,2);self.assertNotIn('pending_envelope',self.s)
 def test_wrong_pending_deadline_is_not_sent(self):
  self.step(4580);bad={'v':2,'iat':4595,'exp':4610,'session':{'deadline':4600,'token_iat':1000,'sid':'synthetic-session','generation':'synthetic-generation'}}
  self.make.side_effect=None;self.make.return_value={'identity_assertion':base64.urlsafe_b64encode(json.dumps(bad).encode()).decode()+'.sig'}
  self.step(4595);self.assertEqual(self.s['phase'],'FAILED');self.assertEqual(self.send.call_count,1)
 def test_pending_generated_only_once(self):
  self.step(4580);self.step(4590);self.step(4595)
  self.assertEqual(self.make.call_count,2);self.assertEqual(self.send.call_count,1)
 def test_identity_change_drops_pending(self):
  self.step(4580);self.step(4590);self.u['nonce']='different';self.step(4595)
  self.assertEqual(self.s['phase'],'FAILED');self.assertNotIn('pending_envelope',self.s)
 def test_late_tick_drops_pending_without_send(self):
  self.step(4580);self.step(4590);self.step(4621)
  self.assertEqual(self.s['phase'],'FAILED');self.assertNotIn('pending_envelope',self.s);self.assertEqual(self.send.call_count,1)
 def test_signer_second_rollover_is_accepted(self):
  self.step(4580)
  with patch.object(b.time,'time',side_effect=[4590,4591,4591,4591]):
   b.advance(self.s,4590,self.u,self.ctx,self.make,self.send,lambda r:r.get('ok') is True)
  self.assertEqual(self.s['phase'],'WAITING_EXPIRY');self.assertIn('pending_envelope',self.s)
  self.assertEqual(self.s['pending_seconds_left'],9)
 def test_different_pending_session_not_sent(self):
  self.step(4580)
  def wrong(native):
   e=self.envelope(native);c=json.loads(base64.urlsafe_b64decode(e['identity_assertion'].split('.')[0]+'=='));c['session']['sid']='other'
   return {'identity_assertion':base64.urlsafe_b64encode(json.dumps(c).encode()).decode()+'.sig'}
  self.make.side_effect=wrong;self.step(4595)
  self.assertEqual(self.s['phase'],'FAILED');self.assertEqual(self.send.call_count,1)
 def test_generic_denial_is_not_time_evidence(self):
  for error in ['CONFIG_NOT_APPROVED','ACL_DENIED','PRINCIPAL_NOT_APPROVED']:
   self.s.update(phase='WAITING_EXPIRY',before_ok=True);self.ctx.side_effect=PermissionError(error)
   self.step(4600);self.assertEqual(self.s['phase'],'FAILED')
 def test_same_times_different_nonce_fails(self):
  self.u['nonce']='new';self.step(4580);self.assertEqual(self.s['phase'],'FAILED');self.send.assert_not_called()
 def test_late_scheduler_does_not_claim_boundary(self):
  self.s['before_ok']=True;self.step(4621);self.assertEqual(self.s['phase'],'FAILED');self.send.assert_not_called()
 def test_missed_preboundary_does_not_claim_pass(self):
  self.step(4600);self.assertEqual(self.s['phase'],'FAILED')
 def test_short_token_not_sixty_minutes(self):
  self.s.update(before_ok=True,duration=1800);self.step(4600);self.assertEqual(self.s['phase'],'FAILED')
 def test_failed_state_never_retries(self):
  self.s['phase']='FAILED';self.step(4580);self.send.assert_not_called()
 def test_panel_halt_prevents_requests(self):
  fake=SimpleNamespace(session_state={'auth_connect_halted':True},error=Mock())
  with patch.object(b,'st',fake):b.panel(self.ctx,self.make,self.send,lambda r:True)
  self.ctx.assert_not_called();self.send.assert_not_called()
 def test_timer_repeated_tick_sends_once(self):
  self.step(4580);self.step(4585);self.assertEqual(self.send.call_count,1)
 def test_clock_rollback_fails(self):
  self.s['last_now']=4590;self.step(4580);self.assertEqual(self.s['phase'],'FAILED')
if __name__=='__main__':unittest.main()

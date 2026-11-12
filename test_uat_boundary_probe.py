import sys, unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
sys.modules.setdefault('streamlit',SimpleNamespace(fragment=lambda **kw: lambda f:f))
import uat_boundary_probe as b
class User(dict):is_logged_in=True
class Tests(unittest.TestCase):
 def setUp(self):
  self.u=User(iss='synthetic',sub='synthetic',iat=1000,exp=9000,nonce='n')
  self.s=dict(phase='WAITING',started=1000,deadline=4600,duration=3600,token_identity=b.token_identity(self.u))
  self.ctx=Mock(return_value=object());self.make=Mock(return_value={});self.send=Mock(return_value={'ok':True})
 def step(self,t):
  with patch.object(b.time,'time',return_value=t):b.advance(self.s,t,self.u,self.ctx,self.make,self.send,lambda r:r.get('ok') is True)
 def test_exact_boundary_without_old_envelope_send(self):
  self.step(4580);self.assertEqual(self.s['phase'],'WAITING_EXPIRY')
  self.ctx.side_effect=PermissionError('RELOGIN_REQUIRED');self.step(4600)
  self.assertEqual(self.s['phase'],'DONE');self.assertEqual(self.send.call_count,1)
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

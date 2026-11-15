"""Direct manual discovery cannot expose a response after authority is lost."""
import copy,json,time,unittest
import test_recovery_channel as support
from recovery_channel import RecoveryChannel
from recovery_client import discover,KEY
from test_bridge import native

class DiscoveryAuthLifetimeTests(unittest.TestCase):
 def run_change(self,change,expected=None):
  current=copy.deepcopy(native);sent=[];active=[True]
  def guard():
   if not active[0]:raise PermissionError('RECOVERY_APPROVAL_ENDED')
  def transport(envelope):
   sent.append(json.loads(envelope['request_json'])['action'])
   change(current,active)
   return dict(ok=True,read_only=True,record_key=KEY,requests=[])
  channel=RecoveryChannel(lambda:current,transport,guard=lambda:None,recovery_guard=guard)
  if expected:
   with self.assertRaisesRegex(PermissionError,'^'+expected+'$'):discover(channel)
  else:
   result=discover(channel)
   self.assertEqual(result['state'],'NO_PENDING_OBSERVED')
   self.assertFalse(result['may_prepare']);self.assertFalse(result['may_execute'])
  self.assertEqual(sent,['list_requests'])
 def test_logout_while_listing(self):
  self.run_change(lambda n,a:setattr(n.user,'is_logged_in',False),'INDIVIDUAL_LOGIN_REQUIRED')
 def test_actor_switch_while_listing(self):
  self.run_change(lambda n,a:n.user.update(sub='OFFLINE-OTHER'),'PRINCIPAL_CHANGED')
 def test_expiry_while_listing(self):
  self.run_change(lambda n,a:n.user.update(exp=int(time.time())-1),'OIDC_TOKEN_EXPIRED_OR_MISSING')
 def test_read_approval_ends_while_listing(self):
  self.run_change(lambda n,a:a.__setitem__(0,False),'RECOVERY_APPROVAL_ENDED')
 def test_unchanged_context_returns_read_only_discovery(self):
  self.run_change(lambda n,a:None)

if __name__=='__main__':unittest.main()

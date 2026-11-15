"""Conflicting delayed statuses must not overwrite a verified terminal result."""
import copy,unittest
import test_client as support
from client import BridgeError
class TerminalStateTests(unittest.TestCase):
 setUp=support.T.setUp
 call=support.T.call
 def tearDown(self):
  self.c.close();self.rpc.terminate();self.rpc.wait();self.rpc.stdin.close();self.rpc.stdout.close();self.tmp.cleanup()
 def test_saved_cannot_be_replaced_by_failed_or_unfinished(self):
  self.c.read();self.c.write(copy.deepcopy(support.BASE))
  digest=self.c.db.execute('SELECT digest FROM attempts').fetchone()[0]
  original=self.c.transport;before=self.call('inspect',{})
  for state,phase in [('FAILED','REJECTED_BEFORE_INTENT'),('UNFINISHED','PREPARED')]:
   with self.subTest(state=state):
    def delayed(a,p):
     r=original(a,p)
     if a=='request_status':r.update(state=state,phase=phase)
     return r
    self.c.transport=delayed
    with self.assertRaisesRegex(BridgeError,'TERMINAL_STATE_CONFLICT'):self.c.reconcile(digest)
    self.assertEqual(self.c._row(digest)[2],'SAVED')
  self.c.transport=original
  self.assertEqual(self.c.reconcile(digest)['state'],'SAVED')
  self.assertEqual(self.call('inspect',{}),before)
 def test_delayed_failure_cannot_overwrite_concurrent_saved(self):
  self.c.read();self.drop='execute_request'
  with self.assertRaises(TimeoutError):self.c.write(copy.deepcopy(support.BASE))
  digest=self.c.pending()[0];original=self.c.transport;injected=False
  def delayed(a,p):
   nonlocal injected
   r=original(a,p)
   if a=='request_status' and not injected:
    injected=True
    self.c.reconcile(digest)  # independent completed confirmation arrives first
    r.update(state='FAILED',phase='REJECTED_BEFORE_INTENT')
   return r
  self.c.transport=delayed
  with self.assertRaisesRegex(BridgeError,'TERMINAL_STATE_CONFLICT'):self.c.reconcile(digest)
  self.assertEqual(self.c._row(digest)[2],'SAVED')
  self.assertEqual(sum(a=='execute_request' for a,p in self.calls),1)
if __name__=='__main__':unittest.main()

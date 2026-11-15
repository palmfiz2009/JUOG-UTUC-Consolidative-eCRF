"""Offline delayed responses must not cross an authentication change."""
import copy, unittest
import test_client as support
from client import BridgeError

class ResponseIdentityTests(unittest.TestCase):
 setUp=support.T.setUp
 call=support.T.call
 def tearDown(self):
  self.c.close();self.rpc.terminate();self.rpc.wait();self.rpc.stdin.close();self.rpc.stdout.close();self.tmp.cleanup()
 def switch_after(self,action,change):
  original=self.c.transport
  def delayed(a,p):
   response=original(a,p)
   if a==action:change()
   return response
  self.c.transport=delayed
  return original
 def test_read_response_cannot_cross_principal_change(self):
  self.c.read();self.c.write(copy.deepcopy(support.BASE))
  before=self.call('inspect',{})
  self.switch_after('read_crf',lambda:self.identity.update(subject='OTHER_OFFLINE_ACTOR'))
  with self.assertRaisesRegex(BridgeError,'^PRINCIPAL_CHANGED$'):self.c.read()
  self.assertIsNone(self.c.observed)
  self.assertEqual(self.call('inspect',{}),before)
 def test_read_response_cannot_cross_authentication_loss(self):
  self.c.read();self.c.write(copy.deepcopy(support.BASE))
  before=self.call('inspect',{})
  self.switch_after('read_crf',self.identity.clear)
  with self.assertRaisesRegex(BridgeError,'^VERIFIED_IDENTITY_REQUIRED$'):self.c.read()
  self.assertIsNone(self.c.observed)
  self.assertEqual(self.call('inspect',{}),before)
 def test_prepare_response_not_bound_after_principal_change(self):
  self.c.read()
  self.switch_after('prepare_request',lambda:self.identity.update(subject='OTHER_OFFLINE_ACTOR'))
  with self.assertRaisesRegex(BridgeError,'^PRINCIPAL_CHANGED$'):self.c.write(copy.deepcopy(support.BASE))
  row=self.c._row(self.c.pending()[0])
  self.assertEqual(row[2],'PREPARING');self.assertIsNone(row[3])
  self.assertIsNone(self.c.observed)
  self.assertEqual(sum(a=='prepare_request' for a,p in self.calls),1)
  self.assertEqual(sum(a=='execute_request' for a,p in self.calls),0)
  self.assertEqual(self.call('inspect',{})['audits'],0)
 def test_unchanged_identity_allows_readback(self):
  self.c.read();saved=self.c.write(copy.deepcopy(support.BASE))
  self.assertEqual(saved['state'],'SAVED')
  self.assertEqual(self.c.read()['record_version'],1)
  self.assertEqual(self.call('inspect',{})['audits'],1)

if __name__=='__main__':unittest.main()

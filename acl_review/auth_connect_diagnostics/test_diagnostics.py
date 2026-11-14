import unittest,json,socket
from urllib.error import HTTPError,URLError
from auth_diagnostics import checked_context,ContextFailure
class T(unittest.TestCase):
 def test_valid(self):self.assertEqual(checked_context(lambda e:{'ok':True},{},lambda r:r['ok']),{'ok':True})
 def test_errors_never_disclose_raw(self):
  for error,code in [(TimeoutError('SECRET'),'TRANSPORT_TIMEOUT'),(URLError(socket.timeout('SECRET')),'TRANSPORT_TIMEOUT'),(HTTPError('SECRET',403,'SECRET',{},None),'HTTP_ERROR'),(ValueError('SECRET'),'TRANSPORT_ERROR')]:
   def fail(e):raise error
   with self.assertRaises(ContextFailure) as caught:checked_context(fail,{},lambda r:False)
   self.assertEqual(caught.exception.code,code);self.assertNotIn('SECRET',str(caught.exception));self.assertGreaterEqual(caught.exception.elapsed_ms,0)
 def test_allowlisted_server_codes(self):
  for code in ['AUTH_EXPIRED','ACL_DENIED','LOCK_TIMEOUT','SESSION_REVOKED']:
   with self.assertRaises(ContextFailure) as caught:checked_context(lambda e:{'ok':False,'error':code,'message':'SECRET'},{},lambda r:False)
   self.assertEqual(caught.exception.code,code)
 def test_unknown_values_not_exposed(self):
  for code in ['SECRET',{'secret':'SECRET'},None]:
   with self.assertRaises(ContextFailure) as caught:checked_context(lambda e:{'error':code},{},lambda r:False)
   self.assertEqual(caught.exception.code,'CONTEXT_REJECTED')
if __name__=='__main__':unittest.main()

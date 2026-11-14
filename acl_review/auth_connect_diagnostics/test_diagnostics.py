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
  for code in ['CONFIGURATION_CHANGED','AUTH_EXPIRED','ACL_DENIED','LOCK_TIMEOUT','SESSION_REVOKED']:
   with self.assertRaises(ContextFailure) as caught:checked_context(lambda e:{'ok':False,'error':code,'message':'SECRET'},{},lambda r:False)
   self.assertEqual(caught.exception.code,code)
 def test_unknown_values_not_exposed(self):
  for code in ['SECRET',{'secret':'SECRET'},None]:
   with self.assertRaises(ContextFailure) as caught:checked_context(lambda e:{'error':code},{},lambda r:False)
   self.assertEqual(caught.exception.code,'CONTEXT_REJECTED')
 def test_configuration_change_never_retries_or_exposes_response(self):
  calls=[]
  def send(envelope):
   calls.append(1)
   return {'ok':False,'error':'CONFIGURATION_CHANGED','detail':'FICTIONAL_SECRET_MARKER'}
  with self.assertRaises(ContextFailure) as caught:checked_context(send,{},lambda r:r.get('ok') is True)
  self.assertEqual(calls,[1]);self.assertEqual(str(caught.exception),'CONFIGURATION_CHANGED')
  self.assertNotIn('FICTIONAL_SECRET_MARKER',str(caught.exception))
if __name__=='__main__':unittest.main()

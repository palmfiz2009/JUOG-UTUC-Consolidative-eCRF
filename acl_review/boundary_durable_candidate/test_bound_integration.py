import sys, json, base64, tempfile, unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
sys.modules.setdefault('streamlit',SimpleNamespace(fragment=lambda **kw:lambda f:f))
import uat_boundary_probe as probe
from durable_observer import Journal, Observer, provision

class User(dict): is_logged_in=True
class Tests(unittest.TestCase):
 def test_same_session_boundary_and_redacted_recovery(self):
  with tempfile.TemporaryDirectory() as folder:
   path=Path(folder)/'e.db';provision(path);u=User(iss='synthetic',sub='SYNTHETIC_PRIVATE_SUBJECT',iat=1000,exp=9000,nonce='SYNTHETIC_NONCE')
   state=dict(phase='WAITING',started=1000,deadline=4600,duration=3600,token_identity=probe.token_identity(u))
   now=[1000];ctx=Mock(return_value=object());sent=[]
   def make(native):
    c=dict(v=2,iat=now[0],exp=min(now[0]+15,4600),session=dict(sid='SYNTHETIC_PRIVATE_SID',generation='synthetic',deadline=4600,token_iat=1000))
    return {'identity_assertion':base64.urlsafe_b64encode(json.dumps(c).encode()).decode()+'.SYNTHETIC_SIGNATURE'}
   def send(e):
    sent.append(now[0]);return {'ok':True} if now[0]<4600 else {'ok':False,'error':'AUTH_EXPIRED'}
   ob=Observer(Journal(path),state,'b'*64,probe.advance,clock=lambda:now[0])
   for t in [4580,4590,4601]:
    now[0]=t
    if t>=4600:ctx.side_effect=PermissionError('APP_SESSION_EXPIRED')
    with patch.object(probe.time,'time',return_value=t):ob.tick(u,ctx,make,send,lambda r:r.get('ok') is True)
   rows=Journal(path).recover(ob.run)
   self.assertEqual(rows[-1]['result']['phase'],'DONE');self.assertEqual(sent,[4580,4601])
   self.assertTrue(all(r['deadline']==4600 for r in rows))
   for forbidden in ['SYNTHETIC_PRIVATE','SYNTHETIC_SIGNATURE','SYNTHETIC_NONCE',probe.token_identity(u)]: self.assertNotIn(forbidden,json.dumps(rows))
 def test_changed_session_is_terminal_failure(self):
  with tempfile.TemporaryDirectory() as folder:
   path=Path(folder)/'e.db';provision(path);u=User(iat=1000,exp=9000,nonce='first')
   state=dict(phase='WAITING',started=1000,deadline=4600,duration=3600,token_identity=probe.token_identity(u))
   ob=Observer(Journal(path),state,'b'*64,probe.advance,clock=lambda:1000)
   u['nonce']='second';send=Mock();ob.tick(u,Mock(),Mock(),send,Mock())
   send.assert_not_called();self.assertEqual(Journal(path).recover(ob.run)[-1]['result']['phase'],'FAILED')
if __name__=='__main__':unittest.main(verbosity=2)

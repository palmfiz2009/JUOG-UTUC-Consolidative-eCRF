import base64
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'python_candidate'))
import app_session_b as b
from auth_bridge import signed_request

class User(dict):
    is_logged_in = True

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = self.tmp.name + '/sessions.db'
        b.provision(self.path)
        self.c = User(iss='https://accounts.google.com', sub='synthetic-only', aud='test-client', iat=1000, exp=9000, nonce='synthetic-nonce')
        self.cfg = dict(session_environment='JUOG_AUTH04_ISOLATED_TEST01', session_b_safety_review_approved=True, session_b_limited_execution_approved=True, session_b_durable_store_confirmed=True, session_b_db_path=self.path, session_policy='isolated_app_session_b', oidc_issuer=self.c['iss'], oidc_client_id='test-client', signing_key='x'*32, bridge_issuer='test', audience='test', max_auth_age_seconds=3600)
    def tearDown(self): self.tmp.cleanup()
    def test_reload_and_reopen_do_not_extend(self):
        self.assertEqual(b.check(self.c,self.cfg,1100),4600)
        self.assertEqual(b.check(self.c,self.cfg,4500),4600)
    def test_boundary(self):
        self.assertEqual(b.check(self.c,self.cfg,4599),4600)
        with self.assertRaises(PermissionError): b.check(self.c,self.cfg,4600)
    def test_short_token(self):
        self.c['exp']=1200
        self.assertEqual(b.check(self.c,self.cfg,1100),1200)
        with self.assertRaises(PermissionError): b.check(self.c,self.cfg,1200)
    def test_bad_claims(self):
        for key,value in [('iat',True),('iat',1200),('iat',-1),('exp',False),('nonce',''),('aud',[])]:
            with self.subTest(key=key,value=value):
                c=self.c.copy(); c[key]=value
                with self.assertRaises(PermissionError): b.check(c,self.cfg,1100)
    def test_revocation_survives_reopen(self):
        b.check(self.c,self.cfg,1100)
        b.check(self.c,self.cfg,1110,revoke=True)
        with self.assertRaises(PermissionError): b.check(self.c,self.cfg,1120)
    def test_missing_store_not_recreated(self):
        os.unlink(self.path)
        with self.assertRaises(PermissionError): b.check(self.c,self.cfg,1100)
        self.assertFalse(os.path.exists(self.path))
    def test_corrupt_store(self):
        Path(self.path).write_bytes(b'broken')
        with self.assertRaises(PermissionError): b.check(self.c,self.cfg,1100)
    def test_approval_and_environment_guards(self):
        for k in ['session_b_safety_review_approved','session_b_limited_execution_approved','session_b_durable_store_confirmed','session_environment']:
            cfg=self.cfg.copy(); cfg[k]=False
            with self.assertRaises(PermissionError): b.check(self.c,cfg,1100)
    def test_bridge_expiry_and_legacy(self):
        st=type('St',(),{'user':self.c,'secrets':{'juog_identity_bridge':self.cfg}})()
        with patch('auth_bridge.time.time',return_value=4599):
            r=signed_request(st,'ui_context',{})
            data=r['identity_assertion'].split('.')[0]
            self.assertEqual(json.loads(base64.urlsafe_b64decode(data+'='*(-len(data)%4)))['exp'],4600)
            del self.cfg['session_policy']
            with self.assertRaises(PermissionError): signed_request(st,'ui_context',{})
    def test_logout_revokes_before_cookie(self):
        events=[]
        st=type('St',(),{'user':self.c,'secrets':{'juog_identity_bridge':self.cfg},'logout':lambda s:events.append('logout')})()
        with patch('time.time',return_value=1100): b.revoke_and_logout(st)
        self.assertEqual(events,['logout'])
        with self.assertRaises(PermissionError): b.check(self.c,self.cfg,1101)
    def test_audience_order_stable(self):
        self.c['aud']=['test-client','other']
        one=b.session_key(self.c,'test',1100)
        self.c['aud'].reverse()
        self.assertEqual(one,b.session_key(self.c,'test',1100))
    def test_expired_logout_cleans_cookie(self):
        events=[]
        st=type('St',(),{'user':self.c,'secrets':{'juog_identity_bridge':self.cfg},'logout':lambda s:events.append('logout')})()
        os.unlink(self.path)
        with patch('time.time',return_value=4600): b.revoke_and_logout(st)
        self.assertEqual(events,['logout'])
    def test_active_logout_storage_failure_keeps_cookie(self):
        events=[]
        st=type('St',(),{'user':self.c,'secrets':{'juog_identity_bridge':self.cfg},'logout':lambda s:events.append('logout')})()
        os.unlink(self.path)
        with patch('time.time',return_value=1100):
            with self.assertRaises(PermissionError): b.revoke_and_logout(st)
        self.assertEqual(events,[])
    def test_explicit_provision_never_overwrites(self):
        b.check(self.c,self.cfg,1100,revoke=True)
        with self.assertRaises(FileExistsError): b.provision(self.path)
        with self.assertRaises(PermissionError): b.check(self.c,self.cfg,1101)
    def test_fresh_verified_token_after_revoke(self):
        b.check(self.c,self.cfg,1100,revoke=True)
        self.c.update(iat=1200, nonce='new-synthetic-nonce')
        self.assertEqual(b.check(self.c,self.cfg,1201),4800)
    def test_store_contention_fails_closed(self):
        import sqlite3
        db=sqlite3.connect(self.path)
        db.execute('BEGIN IMMEDIATE')
        try:
            with self.assertRaises(PermissionError): b.check(self.c,self.cfg,1100)
        finally:
            db.rollback(); db.close()

if __name__=='__main__': unittest.main(verbosity=2)
